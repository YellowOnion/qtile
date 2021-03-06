import datetime
from .. import hook, bar, manager
import base

class Clock(base._TextBox):
    """
        A simple but flexible text-based clock.
    """
    defaults = manager.Defaults(
        ("font", "Monospace", "Clock font"),
        ("fontsize", None, "Clock pixel size. Calculated if None."),
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )
    def __init__(self, fmt="%H:%M", width=bar.CALCULATED, **config):
        """
            - fmt: A Python datetime format string.

            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        self.fmt = fmt
        base._TextBox.__init__(self, " ", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.tick(self.update)

    def update(self):
        now = datetime.datetime.now().strftime(self.fmt)
        if self.text != now:
            _, _, _, _, self.width, _  = self.drawer.text_extents(now)
            self.text = now
            self.guess_width()
            self.draw()


