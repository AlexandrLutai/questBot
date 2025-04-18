import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputFile, FSInputFile
from aiogram.filters import Command
from questions import questions, results, questions_emodji
from config import API_TOKEN, MANAGER_CHAT_ID
import json
users_status = {}



# Создаем экземпляр бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хэндлер для команды /start
@dp.message(Command("start"))
async def send_welcome(message: Message):
    user_id = message.from_user.id
    users_status[user_id] = {"stage": 0, "answers": []}
    await message.answer("Здравствуйте! Бот задаст 5 вопросов, в каждом - по 5 ответов. Вы можете выбрать один или несколько вариантов, отметив снизу нужный пункт. Если нет подходящего варианта - нажмите “Далее”")

    # Генерируем кнопку "Начать"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать", callback_data="Start")]
    ])
    await message.answer("Нажмите кнопку ниже, чтобы перейти к вопросам", reply_markup=keyboard)


@dp.callback_query(lambda callback: callback.data == "Start")
async def process_callback_button1(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    users_status[user_id] = {"stage": 0, "answers": [], "selected": []}
    await callback_query.answer("Начинаем тест!")
    await callback_query.message.delete_reply_markup()  # Удаляем кнопки "Начать"
    quest_message = await bot.send_message(user_id,"Начинаем тест!")
    await send_question(quest_message, user_id)


async def send_question(message, user_id):
    """Отправляет вопрос с кнопками выбора."""
    stage_status = users_status[user_id]["stage"]
    question_text = f"*Вопрос {stage_status + 1}*{questions_emodji[stage_status]} Ребёнок...:\n"
    for i, option in enumerate(questions[stage_status], start=1):
        question_text += f"{i}. {option}\n"
    question_text += f"\n{questions_emodji[stage_status]*7}\nВыберите один или несколько вариантов и нажмите 'Далее'."

    # Генерируем кнопки с цифрами в одну строку
    number_buttons = [
        InlineKeyboardButton(
            text=f"✅ {i}" if i in users_status[user_id]["selected"] else f"⬜ {i}",
            callback_data=f"select_{i}"
        )
        for i in range(1, len(questions[stage_status]) + 1)
    ]

    # Создаём клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        number_buttons,  # Кнопки с цифрами в одной строке
        [InlineKeyboardButton(text="Далее", callback_data="next")]  # Кнопка "Далее" в отдельной строке
    ])

    # Отправляем сообщение
    await message.edit_text(question_text, reply_markup=keyboard, parse_mode="markdown")


@dp.callback_query(lambda callback: callback.data.startswith("select_"))
async def toggle_option(callback_query: CallbackQuery):
    """Переключает состояние выбранного варианта."""
    user_id = callback_query.from_user.id
    option_index = int(callback_query.data.split("_")[1])

    # Переключаем состояние варианта
    if option_index in users_status[user_id]["selected"]:
        users_status[user_id]["selected"].remove(option_index)
    else:
        users_status[user_id]["selected"].append(option_index)

    # Обновляем кнопки
    await send_question(callback_query.message, user_id)
    await callback_query.answer()


@dp.callback_query(lambda callback: callback.data == "next")
async def next_question(callback_query: CallbackQuery):
    """Переходит к следующему вопросу или завершает тест."""
    user_id = callback_query.from_user.id
    stage_status = users_status[user_id]["stage"]

    # Сохраняем выбранные ответы
    users_status[user_id]["answers"].append(users_status[user_id]["selected"])
    users_status[user_id]["selected"] = []  # Очищаем выбор для следующего вопроса

    # Проверяем, есть ли ещё вопросы
    if stage_status < len(questions) - 1:
        users_status[user_id]["stage"] += 1
        await send_question(callback_query.message, user_id)
    else:
        # Удаляем сообщение с кнопками "Далее"
        await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
        await request_city(callback_query.message, user_id)
    await callback_query.answer()

async def request_city(message: Message, user_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ставрополь", callback_data="Ставрополь")],
            [InlineKeyboardButton(text="Михайловск", callback_data="Михайловск")],
        ]
    )
    await message.answer("Спасибо! Остались два последних шага: укажите город проживания и номер телефона. Бот отправит вам результаты теста и подарочный сертификат от KIBERone, который вы сможете активировать в чате с менеджером до 20 апреля", reply_markup=keyboard)   

@dp.callback_query(lambda callback: callback.data in ["Ставрополь", "Михайловск"])
async def process_city(callback_query: CallbackQuery):
    """Обрабатывает выбор города."""
    user_id = callback_query.from_user.id
    city = callback_query.data
    users_status[user_id]["city"] = city  # Сохраняем город
    await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
    await request_contact(callback_query.message, user_id)  # Запрашиваем контакт

async def request_contact(message: Message, user_id: int):
    """Запрашивает контакт пользователя."""
    # Создаём клавиатуру с кнопкой для отправки контакта
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить контакт", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    # Отправляем сообщение с клавиатурой
    await message.answer("Пожалуйста, отправьте ваш контакт, нажав на кнопку ниже:", reply_markup=keyboard)

async def send_final_message(user_id, contact):
    """Отправляет финальное сообщение с результатами теста."""
    if user_id in users_status:
       
        if not users_status[user_id]["answers"]:
            await bot.send_message(user_id,"Вы не выбрали ни одного ответа. Пожалуйста, начните тест заново.")
            del users_status[user_id]
            return
        final_result = process_results(users_status[user_id]["answers"])
        await bot.send_photo(user_id, photo=FSInputFile("img/image.jpg"), caption=f"\nНиже результат теста, выше - подарочный сертификат:\n\n{final_result}")

        await bot.send_message(MANAGER_CHAT_ID, f"Сообщение из квестового бота: \nНовый контакт: {contact.phone_number} \nИмя:{contact.first_name}\n \nГород: {users_status[user_id]['city']}")  # Отправляем сообщение в группу
        del users_status[user_id]
    else:
        await bot.send_message("Пожалуйста, начните тест с команды /start.")

async def process_question(user_id, phone_number = None):
    await bot.send_message(
                MANAGER_CHAT_ID,
                f"Сообщение из квестового бота: \nНовый контакт: {phone_number} \nВопрос: {users_status[user_id]['question']}"
            ) 
    await bot.send_message(user_id,"Ваш вопрос принят, мы свяжемся с вами в ближайшее время.")
    del users_status[user_id]["question"]
     

@dp.message(lambda message: message.contact)
async def process_contact(message: Message):
    """Обрабатывает отправленный контакт и отправляет результат теста."""
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    add_contact(user_id,phone_number)  # Добавляем контакт в список
    if "question" in users_status[message.from_user.id]:
        await process_question(user_id, phone_number)  # Обрабатываем вопрос
        return
    await send_final_message(user_id, message.contact)  # Отправляем финальное сообщение с результатами теста
   
    

@dp.message(lambda message: message.text)
async def handle_text_message(message: Message):
    if message.from_user.id not in users_status:
        users_status[message.from_user.id] = {"stage": 0, "answers": [], "selected": []}
    users_status[message.from_user.id]["question"] = message.text 
    if not check_contact_exists(message.from_user.id):
        await request_contact(message=message, user_id=message.from_user.id)
    else:
        contact = get_contact(message.from_user.id)
        
        await process_question(message.from_user.id, contact["phone_number"])


def process_results(answers):
    """Обрабатывает результаты теста."""
    flat_answers = []  # Разворачиваем вложенные списки
    for item in answers:
        flat_answers.append(len(item))
    # Проверяем, есть ли ответы
    if not flat_answers:
        return "Вы не выбрали ни одного ответа. Пожалуйста, начните тест заново."
    most_common = flat_answers.index(max(flat_answers))
    return results[most_common]

def add_contact(user_id, contact):
    """Добавляет контакт в список."""
    try:
        with open("contacts.json", "r", encoding="utf-8") as file:
            contacts = json.load(file)
    except FileNotFoundError:
        contacts = {}

    contacts[user_id] = {
        "phone_number": contact,
    }

    with open("contacts.json", "w", encoding="utf-8") as file:
        json.dump(contacts, file, ensure_ascii=False, indent=4)

def check_contact_exists(user_id):
    """Проверяет, существует ли контакт в списке."""
    try:
        with open("contacts.json", "r", encoding="utf-8") as file:
            contacts = json.load(file)
            return str(user_id) in contacts
    except FileNotFoundError:
        return False
    
def get_contact(user_id):
    """Получает контакт из списка."""
    try:
        with open("contacts.json", "r", encoding="utf-8") as file:
            contacts = json.load(file)
            return contacts[str(user_id)]
    except FileNotFoundError:
        return None

# Основная функция для запуска бота
async def main():
    # Удаляем старые обновления
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())