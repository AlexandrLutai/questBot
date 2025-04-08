import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from questions import questions, results
from config import API_TOKEN

users_status = {}



# Создаем экземпляр бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хэндлер для команды /start
@dp.message(Command("start"))
async def send_welcome(message: Message):
    user_id = message.from_user.id
    users_status[user_id] = {"stage": 0, "answers": []}
    await message.answer("Добро пожаловать! Для начала теста нажмите кнопку 'Начать'.")

    # Генерируем кнопку "Начать"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать", callback_data="Start")]
    ])
    await message.answer("Нажмите кнопку ниже, чтобы начать тест:", reply_markup=keyboard)


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
    question_text = f"Вопрос {stage_status + 1}:\n"
    for i, option in enumerate(questions[stage_status], start=1):
        question_text += f"{i}. {option}\n"
    question_text += "\nВыберите один или несколько вариантов и нажмите 'Далее'."

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
    await message.edit_text(question_text, reply_markup=keyboard)


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
        # Завершаем тест и запрашиваем контакт
        await request_contact(callback_query.message, user_id)
    await callback_query.answer()


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


@dp.message(lambda message: message.contact)
async def process_contact(message: Message):
    """Обрабатывает отправленный контакт и отправляет результат теста."""
    user_id = message.from_user.id
    contact = message.contact.phone_number  # Получаем номер телефона

    # Сохраняем контакт
    if user_id in users_status:
        users_status[user_id]["phone"] = contact

        # Проверяем, есть ли ответы
        if not users_status[user_id]["answers"]:
            await message.answer("Вы не выбрали ни одного ответа. Пожалуйста, начните тест заново.")
            del users_status[user_id]
            return

        # Обрабатываем результаты теста
        final_result = process_results(users_status[user_id]["answers"])
        await message.answer(f"Спасибо! Ваш номер телефона: {contact}\n\nВаш результат:\n\n{final_result}")
        del users_status[user_id]  # Удаляем данные пользователя
    else:
        await message.answer("Пожалуйста, начните тест с команды /start.")


def process_results(answers):
    """Обрабатывает результаты теста."""
    from collections import Counter
    flat_answers = [item for sublist in answers for item in sublist]  # Разворачиваем вложенные списки

    # Проверяем, есть ли ответы
    if not flat_answers:
        return "Вы не выбрали ни одного ответа. Пожалуйста, начните тест заново."

    most_common = Counter(flat_answers).most_common(1)[0][0]
    return results[most_common]


# Основная функция для запуска бота
async def main():
    # Удаляем старые обновления
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())