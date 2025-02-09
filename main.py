import telebot # библиотека для управления телеграмм ботом
from telebot import types # библиотека для добавления кнопок
bot = telebot.TeleBot('7733019791:AAFZYEnlOx3XoPRzCWocdsiAJ1pRprwzl18') # Токен телеграмм бота

import pytesseract # импортируем библиотеку для распознавания текста на картинке/фото
from PIL import Image
import io
# https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe - скачать Teseract для Window 64-bit
# https://digi.bib.uni-mannheim.de/tesseract/ - скачать Teseract для Window 32-bit
pytesseract.pytesseract.tesseract_cmd = r'd:/Programs/tesseract.exe' # указываем путь к установленной программе Tesseract

from pyzbar.pyzbar import decode

import re # Этот модуль обеспечивает операции сопоставления регулярных выражений
pattern = r'^[A-Z]\d{3} \d{4} \d{2}$'  # Шаблон, который должен соответствовать введенному сообщению. Пример: A502 2010 30


# ================================================================== БЛОК-1: Выбор типа ошибки ================================================================================================
# Создаём словарь для хранения данных
error_data = {}

@bot.message_handler(['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard = True, row_width=2) # метод создания кнопок
    button1 = types.KeyboardButton('Габариты товара не соответствуют ячейки') # создание кнопки 1
    button2 = types.KeyboardButton('Неверное место размещения') # создание кнопки 2
    button3 = types.KeyboardButton('Номер ячейки нарушает порядок') # создание кнопки 3
    button4 = types.KeyboardButton('Размещён группаж') # создание кнопки 4
    markup.add(button1, button2, button3, button4) # добавление кнопок
    bot.send_message(message.chat.id, 'Выбери тип ошибки.', reply_markup=markup) # комментарий, после нажатия Start
    bot.register_next_step_handler(message, showButtom) # создаём отклик, который вызывает функцию showButtom 


# ================================================================== БЛОК-2: Фиксация ошибки ==================================================================================================
def showButtom(message):
    if message.text != '/start':
        # записываем тип ошибки в словарь
        error_data['errorType'] = message.text.strip()
        print(error_data['errorType'])
        markup = types.ReplyKeyboardMarkup(row_width = 2, resize_keyboard=True)
        photoButton = types.KeyboardButton('Использовать камеру 📷')
        penButton = types.KeyboardButton('Зафиксировать вручную ✏️')
        backButton = types.KeyboardButton('Вернуться назад 🔙')
        markup.add(photoButton, penButton, backButton) # добавление кнопок
        bot.send_message(message.chat.id, "Зафиксируй ошибку с помощью камеры или вручную", reply_markup=markup)
        bot.register_next_step_handler(message, fixitError) # создаём отклик, который вызывает функцию fixitError
    else:
        start(message)

def fixitError(message):
    if message.text == 'Использовать камеру 📷':
        bot.send_message(message.chat.id, "Пришли фото ячейки, где была обнаружена ошибка")
        @bot.message_handler(content_types=['photo'])
        def photofix(message):
            # Сохраняем фото пользователя в переменную
            global error_data # указываем на глобальную переменную за пределами функции
            file_info = bot.get_file(message.photo[-1].file_id) # получаем фото
            photo_path = bot.download_file(file_info.file_path) # сохраняем фото
            # Используем pytesseract для распознавания текста
            image = Image.open(io.BytesIO(photo_path))
            decoded_objects = decode(image)
            if decoded_objects: # если фото видит ШК, то преобразует его в текст и записывает в словарь
                barcode_data = decoded_objects[0].data.decode('utf-8')
                error_data['errorFix'] = barcode_data.strip()
            else: # если фото не видит ШК, то преобразует надпись на фото и записывает в словарь его
                recognized_text = pytesseract.image_to_string(image, lang='eng+rus')
                error_data['errorFix'] = recognized_text.strip()
            print(error_data['errorFix'])
            bot.send_message(message.chat.id, "Фото загружено!")
            ControlCheck(message) # создаём отклик, который вызывает функцию ControlCheck

    elif message.text == 'Зафиксировать вручную ✏️':
        bot.send_message(message.chat.id, "Напиши и отправь адрес ячейки в формате: A123 4567 89")
        @bot.message_handler(func=lambda message: True)
        def check_message_format(message):
            if re.match(pattern, message.text): # условие проверяет формат вводимых данных
                # записываем место ошибки в словарь
                error_data['errorFix'] = message.text.strip()
                print(error_data['errorFix'])
                bot.send_message(message.chat.id, "Сообщение соответствует формату!")
                ControlCheck(message) # создаём отклик, который вызывает функцию ControlCheck
            elif message.text == 'Вернуться назад 🔙':
                start(message)
            else:
                bot.send_message(message.chat.id, "Ошибка! Пожалуйста, введите сообщение в формате: A123 4567 89. Проверьте, что включен английский язык.")

    elif message.text == 'Вернуться назад 🔙': 
        start(message) # создаём отклик, который вызывает функцию start (возвращает пользователя в начало)


# ================================================================== БЛОК-3: Контрольная проверка ==================================================================================================
def ControlCheck(message):
    global error_data
    markup = types.InlineKeyboardMarkup()
    buttonOk = types.InlineKeyboardButton('✅', callback_data='dataIsCorrect')
    buttonNotOk = types.InlineKeyboardButton('❌', callback_data='dataIsNotCorrect')
    markup.add(buttonOk, buttonNotOk)
    bot.send_message(message.chat.id, 
    f"<b>Проверьте, всё ли корректно?</b>\n <u>Тип ошибки:</u>\n {error_data['errorType']}\n <u>Место ошибки:</u>\n {error_data['errorFix']}", parse_mode='html', reply_markup=markup)


# ================================================================== БЛОК-4: Отправка формы на гугл таблицы ==================================================================================================






# Команда, для непрерывной работы скрипта.
bot.polling(non_stop=True) # Так же можно использовать команду bot.infinity_polling()