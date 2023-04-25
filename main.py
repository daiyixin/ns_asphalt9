import datetime
import re
import shutil
import threading
import time

from ocr import ocr
from screenshot import screenshot
from utils.controller import Buttons, pro
from utils.log import logger


FINISHED_COUNT = 0

# 是否初始化车所在位置
INITED_CAR_POSITION = False

# 程序运行
G_RUN = threading.Event()

# 退出循环事件
G_RACE_RUN_EVENT = threading.Event()
G_RACE_QUIT_EVENT = threading.Event()

# 是否活跃状态
NO_OPERATION_COUNT = 0

# 正序选车
SELECT_CAR_ACTION = [
    Buttons.DPAD_DOWN,
    Buttons.DPAD_RIGHT,
    Buttons.DPAD_UP,
    Buttons.DPAD_RIGHT,
] * 10
# 反序选车
SELECT_CAR_REVERSE_ACTION = [
    Buttons.DPAD_DOWN,
    Buttons.DPAD_LEFT,
    Buttons.DPAD_UP,
    Buttons.DPAD_LEFT,
] * 10
SELECT_REVERSE = [
    Buttons.DPAD_UP,
    Buttons.DPAD_RIGHT,
    Buttons.DPAD_DOWN,
    Buttons.DPAD_RIGHT,
] * 10
# 选车次数
SELECT_COUNT = -1
# 最多切换车次数(起始值0)
MAX_SELECT_COUNT = 5

# 键盘与手柄映射
KEY_MAPPING = {
    "6": "MINUS",
    "7": "PLUS",
    "[": "CAPTURE",
    "]": "HOME",
    "i": "X",
    "j": "Y",
    "l": "A",
    "k": "B",
    "s": "DPAD_DOWN",
    "w": "DPAD_UP",
    "a": "DPAD_LEFT",
    "d": "DPAD_RIGHT",
}


def has_text(identity, page_text):
    """page_text中是否包含identity"""
    if re.findall(identity, page_text):
        return True
    return False


def ocr_screen():
    """截图并识别"""
    screenshot()
    text = ocr()
    return text


def wait_for(text, timeout=10):
    """等待屏幕出现text"""
    count = 0
    logger.info(f"Wait for text = {text}")
    while True:
        screen_text = ocr_screen()
        if has_text(text, screen_text):
            return screen_text
        count += 1
        time.sleep(1)
        if count > timeout:
            raise Exception(f"Wait for text = {text} timeout!")


def enter_game():
    """进入游戏"""
    buttons = [
        Buttons.B,
        Buttons.DPAD_UP,
        Buttons.DPAD_LEFT,
        Buttons.DPAD_LEFT,
        Buttons.A,
        Buttons.A,
    ]
    pro.press_group(buttons, 0.5, 0)


def enter_series():
    """进入多人赛事"""
    pro.press_group([Buttons.B] * 5, 0.5, 0)
    pro.press_group([Buttons.DPAD_DOWN] * 5, 0.5, 0)
    pro.press_group([Buttons.DPAD_LEFT] * 5, 0.5, 0)
    pro.press_group([Buttons.DPAD_RIGHT] * 3, 0.5, 0)
    pro.press_group([Buttons.DPAD_UP] * 2, 0.5, 0)
    time.sleep(2)
    pro.press_group([Buttons.A] * 1, 0.5, 0)


def enter_carhunt():
    """进入寻车"""
    pro.press_group([Buttons.B] * 5, 0.5, 0)
    pro.press_group([Buttons.DPAD_DOWN] * 5, 0.5, 0)
    pro.press_group([Buttons.DPAD_LEFT] * 5, 0.5, 0)
    pro.press_group([Buttons.DPAD_RIGHT] * 2, 0.5, 0)
    time.sleep(2)
    pro.press_group([Buttons.A] * 1, 0.5, 0)
    time.sleep(2)
    pro.press_group([Buttons.DPAD_RIGHT] * 5, 0.5, 0)
    time.sleep(2)
    pro.press_group([Buttons.A] * 2, 0.5, 0)


def play_game(select_car=1):
    """点击play并等待进入到选车界面"""
    pro.press_a(0.1)
    if select_car:
        for i in range(20):
            time.sleep(1)
            text = ocr_screen()
            if has_text("CAR SELECTION", text):
                break


def auto_select_car(reverse=False):
    """自动选车"""
    global INITED_CAR_POSITION
    global SELECT_COUNT
    logger.info("Auto select car.")
    # 车库重置到第一辆车
    if reverse and not INITED_CAR_POSITION:
        for i in range(5):
            pro.press_button(Buttons.DPAD_RIGHT, 0.1)
        INITED_CAR_POSITION = True

    # 选车
    if reverse:
        select_action = SELECT_CAR_REVERSE_ACTION
    else:
        select_action = SELECT_CAR_ACTION

    while True:
        logger.info(f"select_count = {SELECT_COUNT}")
        # SELECT_COUNT 判断重置 使用过5辆车
        if SELECT_COUNT >= MAX_SELECT_COUNT:
            actions = SELECT_REVERSE[: SELECT_COUNT + 1]
            actions.reverse()
            for action in actions:
                pro.press_button(action, 0.2)
            time.sleep(2)
            SELECT_COUNT = -1

        # 检查车辆是否可用
        pro.press_a()
        text = wait_for("TOP SPEED|HANDLING")
        if has_text("GET KEY", text):
            pro.press_b()
            wait_for("CAR SELECTION")
            SELECT_COUNT += 1
            pro.press_button(select_action[SELECT_COUNT], 2)
            continue

        # 处理跳到第一辆车的情况, 重置车的位置
        if has_text("EMIRA", text):
            pro.press_b(3)
            wait_for("CAR SELECTION")

            # 重置
            action = Buttons.DPAD_RIGHT if reverse else Buttons.DPAD_LEFT
            for i in range(5):
                pro.press_button(action, 0.2)
            time.sleep(2)

            # 快进select
            for step in range(SELECT_COUNT + 1):
                pro.press_button(select_action[step], 0.2)
            time.sleep(2)
            pro.press_a()

        pro.press_a(5)
        text = ocr_screen()
        # 点两下a能开始比赛说明车可用
        if has_text("SEARCHING", text):
            return

        for i in range(2):
            if has_text("TOP SPEED|HANDLING", text):
                pro.press_b(3)
            if has_text("CAR SELECTION", text):
                break
            text = ocr_screen()

        SELECT_COUNT += 1
        pro.press_button(select_action[SELECT_COUNT], 2)


def select_car(row, column, confirm=1):
    """开始比赛并选择车
    row 第几行
    column 第几列
    row: 1 column: 4 选择第1行第4列那辆车
    """
    logger.info("Start select car.")
    # 车库重置到第一辆车
    for i in range(25):
        pro.press_button(Buttons.DPAD_LEFT, 0, 0)

    for i in range(3):
        pro.press_button(Buttons.DPAD_UP, 0, 0)

    # 选车
    for i in range(row):
        pro.press_button(Buttons.DPAD_DOWN, 0, 0)

    for i in range(column - 1):
        pro.press_button(Buttons.DPAD_RIGHT, 0, 0)

    time.sleep(2)

    if confirm:
        confirm_and_play()


def confirm_and_play():
    # 确认车辆
    logger.info("Confirm car")
    pro.press_a(2)
    # 开始比赛
    logger.info("Start race")
    pro.press_a(3)


def process_race(race_mode=0):
    global FINISHED_COUNT
    for i in range(100):
        text = ocr_screen()
        position = re.findall(r"\d/\d", text)
        position = position[0] if position else ""
        progress = re.findall(r"\d+%", text)
        progress = progress[0] if progress else ""
        logger.info(f"Current position {position}, progress {progress}")

        if race_mode == 1:
            progress = int(progress.replace("%", ""))
            if progress > 0 and progress < 22:
                pro.press_buttons(Buttons.Y)
                time.sleep(0.4)
                pro.press_buttons(Buttons.Y)
                pro.press_buttons(Buttons.DPAD_LEFT)
            if progress >= 22:
                pro.press_buttons(Buttons.ZL, 23)
                for _ in range(10):
                    pro.press_buttons(Buttons.Y)
                    pro.press_buttons(Buttons.Y)
            time.sleep(1)
        else:
            pro.press_button(Buttons.Y, 0.7, 0)
            pro.press_button(Buttons.Y, 0, 0)
            time.sleep(3)

        if has_text("NEXT|RATING|WINNER|YOUR", text):
            break
    FINISHED_COUNT += 1
    logger.info(f"Already finished {FINISHED_COUNT} times.")


def car_hunt(race_mode=0):
    """寻车"""
    logger.info("Start process car hunt.")
    pro.press_a(3)
    logger.info("Wait for select car")
    wait_for("CAR SELECTION")
    logger.info("Start select car")
    select_car(2, 5, confirm=0)
    logger.info("Start confirm car")
    pro.press_a(3)
    logger.info("Wait for Play button")
    wait_for("PLAY", 30)
    logger.info("Press play button")
    pro.press_a(3)
    logger.info("OCR screen")
    text = ocr_screen()
    if "TICKETS" in text:
        pro.press_button(Buttons.DPAD_DOWN, 2)
        pro.press_a(2)
        pro.press_b(2)
        pro.press_a(2)
    logger.info("Start process race")
    process_race(race_mode)
    logger.info("Finished car hunt")


def connect_controller():
    """连接手柄"""
    pro.press_buttons([Buttons.L, Buttons.R], down=1)
    time.sleep(1)
    pro.press_buttons([Buttons.A], down=0.5)


def wait(seconds=3):
    time.sleep(3)


def process_screen(text):
    """根据显示内容执行动作"""

    page_mapping = {
        "loading_game": {
            "identity": "LOADING RACE",
            "action": process_race,
            "args": (),
        },
        "connect_controller": {
            "identity": "Press.*on the controller",
            "action": connect_controller,
            "args": (),
        },
        "enter_game": {
            "identity": "Controllers",
            "action": enter_game,
            "args": (),
        },
        # "play_game": {
        #     "identity": "WORLD|LIMITED|TRIAL|CLASSIC",
        #     "action": play_game,
        #     "args": (0,),
        # },
        "enter_series": {
            "identity": "WORLD.*(TRIAL)",
            "action": enter_series,
            "args": (),
        },
        "enter_carhunt": {
            "identity": "PLAY LIMITED.*TIME EVENTS",
            "action": enter_carhunt,
            "args": (),
        },
        "play_trial": {
            "identity": "TRIAL",
            "action": play_game,
            "args": (0,),
        },
        "play_classic": {
            "identity": "CLASSIC|WORLD SERIES",
            "action": play_game,
            "args": (1,),
        },
        "car_hunt": {
            "identity": "CAR HUNT.*PORSCHE 718 CAYMAN GT4",
            "action": car_hunt,
            "args": (),
        },
        "car_hunt_mkx": {
            "identity": "CAR HUNT.*BOLWELL",
            "action": car_hunt,
            "args": (1,),
        },
        "select_cat": {
            "identity": "CAR SELECTION",
            "action": select_car,
            "args": (1, 4),
        },
        # "auto_select_cat": {
        #     "identity": "CAR SELECTION",
        #     "action": auto_select_car,
        #     "args": (1,),
        # },
        "confirm_car": {
            "identity": "TOP SPEED|HANDLING|NITRO",
            "action": pro.press_button,
            "args": (Buttons.A, 3),
        },
        "search_game": {
            "identity": "SEARCHING",
            "action": pro.press_button,
            "args": (Buttons.Y, 3),
        },
        "back": {
            "identity": "DEMOTED|DISCONNECTED|NO CONNECTION|YOUR CLUB ACHIEVED|CONGRATULATIONS.*IMPROVE|TIER",
            "action": pro.press_button,
            "args": (Buttons.B,),
        },
        "next_page": {
            "identity": "NEXT|RATING|WINNER|YOUR|CONGRATULATIONS|CONNECTION ERROR|STAR UP",
            "not_in": "YOUR CAR",
            "action": pro.press_button,
            "args": (Buttons.A,),
        },
        "offline_mode_no": {
            "identity": "OFFLINE MODE",
            "action": pro.press_button,
            "args": ([Buttons.DPAD_LEFT, Buttons.B], 1, 1),
        },
        "system_error": {
            "identity": "software.*closed",
            "action": pro.press_button,
            "args": ([Buttons.A] * 3, 1, 1),
        },
    }
    match_page = []
    for page in page_mapping:
        if has_text(page_mapping[page]["identity"], text):
            if "not_in" in page_mapping[page]:
                if not has_text(page_mapping[page]["not_in"], text):
                    logger.info(f"match identity: {page_mapping[page]['identity']}")
                    match_page.append(page)
            else:
                logger.info(f"match identity: {page_mapping[page]['identity']}")
                match_page.append(page)
    logger.info(f"match results: {match_page}")
    if len(match_page) >= 1:
        page_data = page_mapping[match_page[0]]
        action = page_data["action"]
        args = page_data["args"]
        action(*args)
    else:
        logger.info("Match none page. Sleep 3 seconds and try again.")
        time.sleep(3)


def capture():
    filename = "".join([str(d) for d in datetime.datetime.now().timetuple()]) + ".jpg"
    shutil.copy("./images/output.jpg", f"./images/{filename}")
    return filename


def event_loop():
    global G_RACE_QUIT_EVENT
    global G_RACE_RUN_EVENT

    while G_RACE_RUN_EVENT.is_set() and G_RUN.is_set():
        try:
            text = ocr_screen()
            has_words = re.findall("\w", text)
            if has_words:
                process_screen(text)
            else:
                logger.info(f"Detect nothing, continue.")
                time.sleep(2)
        except Exception as err:
            filename = capture()
            logger.error(
                f"Caught exception, err = {err}, page text = {text}, filename = {filename}"
            )
            # 出错重新进多人
            # enter_series()

    G_RACE_QUIT_EVENT.set()


def keep_alive():
    """每60秒检测一次是否是活跃状态"""
    global NO_OPERATION_COUNT
    while G_RUN.is_set():
        NO_OPERATION_COUNT += 1
        time.sleep(1)
        if NO_OPERATION_COUNT > 60:
            # 如果退出了event loop并且没有指令输入， 按一下y键防止断开手柄连接
            logger.info("Keep alive press button y")
            pro.press_buttons(Buttons.Y)
            NO_OPERATION_COUNT = 0


def start_keep_alive():
    t = threading.Thread(target=keep_alive, args=())
    t.start()


def command_input():
    global G_RUN
    global G_RACE_RUN_EVENT
    global G_RACE_QUIT_EVENT
    global G_CLEAR_COUNT

    while G_RUN.is_set():
        command = input("Please input command \n")
        G_CLEAR_COUNT = 0
        if command == "stop":
            # 停止挂机
            if G_RACE_RUN_EVENT.is_set():
                G_RACE_RUN_EVENT.clear()
                logger.info("Stop event loop.")
                G_RACE_QUIT_EVENT.wait()
                logger.info("Event loop stoped.")
            else:
                logger.info("Event loop not running.")

        elif command == "run":
            # 开始挂机
            if G_RACE_RUN_EVENT.is_set():
                logger.info("Event loop is running.")
            else:
                G_RACE_RUN_EVENT.set()
                G_RACE_QUIT_EVENT.clear()
                logger.info("Start run event loop.")

        elif command == "quit":
            # 退出程序
            logger.info("Quit main.")
            G_RUN.clear()

        elif command in KEY_MAPPING:
            # 手柄操作
            if G_RACE_RUN_EVENT.is_set():
                logger.info("Please stop event loop first.")
            else:
                control_data = KEY_MAPPING.get(command)
                pro.press_button(control_data, 0.5)
        else:
            logger.info(f"{command} command not support!")


def start_command_input():
    t = threading.Thread(target=command_input, args=())
    t.start()


def main():
    global G_RACE_RUN_EVENT
    global G_RACE_QUIT_EVENT

    G_RACE_QUIT_EVENT.set()
    G_RUN.set()

    start_keep_alive()
    start_command_input()

    while G_RUN.is_set():
        if G_RACE_RUN_EVENT.is_set():
            event_loop()
        else:
            time.sleep(1)


if __name__ == "__main__":
    main()
