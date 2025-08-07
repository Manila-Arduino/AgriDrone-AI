import platform
from typing import Optional
from gpiozero import LED as GpioLED, PWMLED
from signal import pause


class LED:
    """
    Simple wrapper around gpiozero LED/PWMLED with a unified API.
    - Use pwm=True if you want brightness control (.value 0.0–1.0, .pulse()).
    """

    def __init__(
        self,
        pin: int,
        *,
        pwm: bool = False,
        active_high: bool = True,
        initial_value: float | bool = False
    ):
        self._pwm = pwm
        if pwm:
            self._led: PWMLED = PWMLED(pin, active_high=active_high, initial_value=initial_value)  # type: ignore[assignment]
        else:
            self._led: GpioLED = GpioLED(pin, active_high=active_high, initial_value=initial_value)  # type: ignore[assignment]

    # --- basic ---
    def on(self):
        self._led.on()

    def off(self):
        self._led.off()

    def toggle(self):
        self._led.toggle()

    def is_lit(self) -> bool:
        return bool(self._led.is_lit)

    # --- blink / pulse ---
    def blink(
        self,
        on_time: float = 0.5,
        off_time: float = 0.5,
        n: Optional[int] = None,
        background: bool = True,
    ):
        """Works for both LED and PWMLED."""
        self._led.blink(on_time=on_time, off_time=off_time, n=n, background=background)

    def pulse(
        self,
        fade_in: float = 1.0,
        fade_out: float = 1.0,
        n: Optional[int] = None,
        background: bool = True,
    ):
        """Only meaningful if pwm=True."""
        if self._pwm:
            self._led.pulse(
                fade_in_time=fade_in, fade_out_time=fade_out, n=n, background=background
            )

    # --- brightness (PWM only) ---
    def set_brightness(self, value: float):
        """0.0–1.0. Ignored if pwm=False."""
        if self._pwm:
            self._led.value = max(0.0, min(1.0, value))

    # --- cleanup ---
    def close(self):
        self._led.close()


# EXAMPLE:
if __name__ == "__main__":
    status_led = LED(21, pwm=True)
    status_led.pulse()
    pause()
