from .constrain import parse


def colorize(*guesses: str):
    CGREEN = "\33[32m"
    CYELLOW = "\33[33m"
    CRED = "\33[31m"
    CEND = "\33[0m"

    def colorize_g(guess: str) -> str:
        color_guess = ""
        for color, c in parse(guess):
            if color == "green":
                color_guess += CGREEN
                color_guess += c.upper()
                color_guess += CEND
            elif color == "yellow":
                color_guess += CYELLOW
                color_guess += c
                color_guess += CEND
            elif color == "gray":
                color_guess += CRED
                color_guess += c.lower()
                color_guess += CEND
            else:
                assert False, (guess, c, color)
        return color_guess

    return [colorize_g(guess) for guess in guesses]