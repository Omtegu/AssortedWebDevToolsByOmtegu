import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, WebDriverException

def get_words(driver):
    try:
        words = driver.find_elements(By.CLASS_NAME, "word")
        return [word.text for word in words]
    except Exception:
        return []

def type_word(input_field, word, accuracy, base_delay, randomness):
    letters = "abcdefghijklmnopqrstuvwxyz"
    for char in word:
        # Mistype?
        if random.random() > accuracy:
            wrong_char = random.choice(letters.replace(char.lower(), ""))
            input_field.send_keys(wrong_char)
            time.sleep(base_delay + random.uniform(0, randomness))

            input_field.send_keys(Keys.BACKSPACE)
            time.sleep(base_delay + random.uniform(0, randomness))

        input_field.send_keys(char)
        time.sleep(base_delay + random.uniform(0, randomness))

def prompt_for_config():
    while True:
        try:
            wpm = int(input("Enter desired Words Per Minute (e.g., 60): "))
            if wpm <= 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a positive integer for WPM.")

    while True:
        try:
            accuracy = float(input("Enter desired accuracy as decimal (e.g., 0.95 for 95%): "))
            if not 0 < accuracy <= 1:
                raise ValueError
            break
        except ValueError:
            print("Please enter a decimal between 0 and 1 for accuracy.")

    while True:
        try:
            randomness = float(input("Enter randomness delay factor in seconds (e.g., 0.05): "))
            if randomness < 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a non-negative number for randomness.")

    return wpm, accuracy, randomness

def clear_input_field(input_field):
    try:
        input_field.clear()
    except Exception:
        # fallback: select all and delete
        input_field.click()
        input_field.send_keys(Keys.CONTROL + "a")
        input_field.send_keys(Keys.BACKSPACE)

def monkeytype_bot():
    print("Starting browser...")
    driver = webdriver.Firefox()  # Or webdriver.Chrome()
    driver.get("https://monkeytype.com")

    print("Log in to your account, then type '\\' (backslash) and press Enter here to start the bot.")
    while True:
        user_input = input()
        if user_input.strip() == '\\':
            break
        else:
            print("Waiting for '\\' to start...")

    # Accept cookie banner modal if present
    time.sleep(3)
    try:
        accept_button = driver.find_element(By.CSS_SELECTOR, "button.active.acceptAll")
        accept_button.click()
        print("Cookie banner accepted.")
    except NoSuchElementException:
        print("No cookie banner found or already accepted.")

    # Wait for input field
    input_field = None
    for _ in range(20):
        try:
            input_field = driver.find_element(By.ID, "wordsInput")
            break
        except NoSuchElementException:
            time.sleep(0.5)
    if not input_field:
        print("Input field not found. Exiting.")
        driver.quit()
        return

    while True:  # This is the main RESTART loop
        try:
            # Prompt config each new run
            wpm, accuracy, randomness = prompt_for_config()
            base_delay = 60 / (wpm * 6)  # Approximate char delay for given WPM

            typed_words = 0

            # Clear input field before starting fresh
            clear_input_field(input_field)

            print(f"Starting typing at {wpm} WPM, {accuracy*100}% accuracy, randomness={randomness}")

            while True:
                words_list = get_words(driver)

                if not words_list:
                    time.sleep(0.1)
                    continue

                # Detect if test reset mid-run
                if typed_words >= len(words_list):
                    print("Test reset detected, restarting from beginning...")
                    typed_words = 0
                    clear_input_field(input_field)
                    time.sleep(1)
                    continue

                while typed_words < len(words_list):
                    word = words_list[typed_words]
                    type_word(input_field, word, accuracy, base_delay, randomness)
                    input_field.send_keys(Keys.SPACE)
                    # Small delay after space to mimic natural typing
                    time.sleep(base_delay + random.uniform(0, randomness) / 2)
                    typed_words += 1

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\nBot stopped by user. Closing browser.")
            driver.quit()
            break

        except Exception as e:
            print(f"\nError encountered: {e}")
            print("Restarting configuration and typing... Browser remains open.")
            typed_words = 0
            try:
                clear_input_field(input_field)
            except WebDriverException:
                print("Input field lost. Attempting to find input field again...")
                for _ in range(10):
                    try:
                        input_field = driver.find_element(By.ID, "wordsInput")
                        break
                    except NoSuchElementException:
                        time.sleep(0.5)
                else:
                    print("Input field not found after retry. Exiting.")
                    driver.quit()
                    return
            # Loop will restart and prompt config again

if __name__ == "__main__":
    monkeytype_bot()

