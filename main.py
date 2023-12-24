import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
from bs4 import BeautifulSoup
import re
from telegram import ReplyKeyboardMarkup


# Устанавливаем уровень логгирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Получаем токен от BotFather
TOKEN = 'TOKEN TG'

# Глобальная переменная для хранения выбранной категории
selected_category = None

# Глобальная переменная для хранения выбранной подкатегории
selected_subcategory = None

# Глобальная переменная для хранения выбранной доступности товара
selected_availability = None

# Настройка сессии для запросов к сайту
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

# Функция для обновления глобальных переменных
def update_selection(category=None, subcategory=None, availability=None):
    global selected_category, selected_subcategory, selected_availability
    selected_category = category
    selected_subcategory = subcategory
    selected_availability = availability

# Функция для парсинга категорий с сайта
def parse_categories():
    url = 'https://easysellers.ru/wb/popular'
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    categories = soup.find('select', {'id': 'subjectRoot-select'}).find_all('option', {'value': True})
    return [(option.text, option['value']) for option in categories]

# Функция для парсинга подкатегорий с сайта
def parse_subcategories(category):
    url = f'https://easysellers.ru/wb/popular/{category}'
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Check if the element with id 'subject-select' is present
    select_element = soup.find('select', {'id': 'subject-select'})
    if select_element:
        subcategories = select_element.find_all('option', {'value': True})
        return [(option.text, option['value']) for option in subcategories]
    else:
        return []

# Функция для парсинга топ-10 селлеров
def parse_top_sellers():
    global selected_category, selected_subcategory
    url = f'https://easysellers.ru/wb/top-sellers/{selected_category}/{selected_subcategory}'
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    rows = table.find_all('tr')[1:11]  # Первые 10 строк, пропускаем заголовок
    sellers_data = []
    for row in rows:
        columns = row.find_all('td')
        rank, name, sales = columns[0].text.strip(), columns[1].text.strip(), columns[4].text.strip()
        sellers_data.append(f'{rank}. {name} - Продажи в неделю: {sales}')
    return '\n'.join(sellers_data)

# Функция для парсинга доступности товара
def parse_availability():
    url = 'https://easysellers.ru/wb/deficit?page=1'
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    availability_options = soup.find('select', {'id': 'availability-select'}).find_all('option', {'value': True})
    return [(option.text, option['value']) for option in availability_options]

# Функция для парсинга данных по нише
def parse_niche_data():
    global selected_availability
    formatted_availability = selected_availability.replace(' ', '+')
    url = f'https://easysellers.ru/wb/deficit/{selected_category}?page=1&availability={formatted_availability}'
    response = session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    rows = table.find_all('tr')[1:]  # Пропускаем заголовок
    niche_data = []
    for row in rows:
        columns = row.find_all('td')
        item, turnover, availability, sales = columns[1].text.strip(), columns[2].text.strip(), columns[3].text.strip(), columns[4].text.strip()
        niche_data.append(f'{item};{turnover};{availability};{sales}')
    return '\n'.join(niche_data)

# Функция для взаимодействия с GigaChat API
def analyze_data(category, subcategory, items):
    # Здесь вы можете использовать API GigaChat для отправки запроса с анализом данных
    # Замените 'YOUR_GIGACHAT_API_KEY' на ваш реальный ключ API
    api_key = 'YOUR_GIGACHAT_API_KEY'
    url = 'https://api.gigachat.net/v1/ask'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    
    # Запрос для отправки анализа данных
    data = {
        'question': f'Проанализируй данные и скажи, что можно добавить для увеличения продаж в категории {category} и подкатегории {subcategory} для следующих товаров: {items}',
        'language': 'ru'
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    # Получение и возвращение ответа
    if response.status_code == 200:
        return response.json()['answer']
    else:
        return f'Ошибка при взаимодействии с GigaChat API: {response.status_code}'

# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Привет! Я бот для выполнения различных задач. Используйте /menu для доступа к функциям."
    )

# Обработчик команды /menu
def menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ['Выбрать категорию', 'Показать ТОП 10 селлеров'],
        ['Выбрать нишу', 'Проанализировать']
    ]
    reply_markup = {'keyboard': keyboard, 'one_time_keyboard': True}
    update.message.reply_text('Выберите действие:', reply_markup=reply_markup)

# Обработчик команды /choose_category
def choose_category(update: Update, context: CallbackContext) -> None:
    categories = parse_categories()
    print(len(categories))
    keyboard = [[category[0]] for category in categories]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Выберите категорию:', reply_markup=reply_markup)


# Обработчик команды /show_top_sellers
def show_top_sellers(update: Update, context: CallbackContext) -> None:
    global selected_category, selected_subcategory
    if not selected_category or not selected_subcategory:
        update.message.reply_text('Сначала выберите категорию и подкатегорию.')
        return
    top_sellers_data = parse_top_sellers()
    update.message.reply_text(top_sellers_data, parse_mode=ParseMode.MARKDOWN)

# Обработчик команды /choose_niche
def choose_niche(update: Update, context: CallbackContext) -> None:
    availability_options = parse_availability()
    keyboard = [[option[0]] for option in availability_options]
    reply_markup = {'keyboard': keyboard, 'one_time_keyboard': True}
    update.message.reply_text('Выберите доступность товара:', reply_markup=reply_markup)

# Обработчик команды /analyze
def analyze(update: Update, context: CallbackContext) -> None:
    global selected_category, selected_subcategory, selected_availability
    if not selected_availability:
        update.message.reply_text('Сначала выберите доступность товара.')
        return
    niche_data = parse_niche_data()
    analysis_result = analyze_data(selected_category, selected_subcategory, niche_data)
    update.message.reply_text(analysis_result, parse_mode=ParseMode.MARKDOWN)

# Обработчик текстовых сообщений
def text_handler(update: Update, context: CallbackContext) -> None:
    global selected_category, selected_subcategory
    message_text = update.message.text
    if message_text in [category[0] for category in parse_categories()]:
        # Пользователь выбрал категорию
        selected_category = re.sub(r'\W+', '-', message_text.lower())
        subcategories = parse_subcategories(selected_category)
        keyboard = [[subcategory[0]] for subcategory in subcategories]
        reply_markup = {'keyboard': keyboard, 'one_time_keyboard': True}
        update.message.reply_text('Выберите подкатегорию:', reply_markup=reply_markup)
    elif message_text in [subcategory[0] for subcategory in parse_subcategories(selected_category)]:
        # Пользователь выбрал подкатегорию
        selected_subcategory = re.sub(r'\W+', '-', message_text.lower())
        update.message.reply_text(f'Выбрана категория: {selected_category}\nВыбрана подкатегория: {selected_subcategory}')
    else:
        update.message.reply_text('Неверная команда. Используйте /menu для доступа к функциям.')

# Основная функция
def main() -> None:
    # Создаем экземпляр бота и передаем токен
    updater = Updater(TOKEN)

    # Получаем объект диспетчера от бота
    dp = updater.dispatcher

    # Добавляем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("choose_category", choose_category))
    dp.add_handler(CommandHandler("show_top_sellers", show_top_sellers))
    dp.add_handler(CommandHandler("choose_niche", choose_niche))
    dp.add_handler(CommandHandler("analyze", analyze))

    # Добавляем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    # Запускаем бота
    updater.start_polling()

    # Оставляем бота работать до завершения работы
    updater.idle()

if __name__ == '__main__':
    main()
