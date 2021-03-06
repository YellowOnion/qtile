# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys, struct
import xcbq
import xcb.xcb
from xcb.xproto import EventMask
import xcb.xproto
import command, utils
import manager, hook



# ICCM Constants
NoValue = 0x0000
XValue = 0x0001
YValue = 0x0002
WidthValue = 0x0004
HeightValue = 0x0008
AllValues = 0x000F
XNegative = 0x0010
YNegative = 0x0020
USPosition = (1 << 0)
USSize = (1 << 1)
PPosition = (1 << 2)
PSize = (1 << 3)
PMinSize = (1 << 4)
PMaxSize = (1 << 5)
PResizeInc = (1 << 6)
PAspect = (1 << 7)
PBaseSize = (1 << 8)
PWinGravity = (1 << 9)
PAllHints = (PPosition|PSize|PMinSize|PMaxSize|PResizeInc|PAspect)
InputHint = (1 << 0)
StateHint = (1 << 1)
IconPixmapHint = (1 << 2)
IconWindowHint = (1 << 3)
IconPositionHint = (1 << 4)
IconMaskHint = (1 << 5)
WindowGroupHint = (1 << 6)
MessageHint = (1 << 7)
UrgencyHint	= (1 << 8)
AllHints = (InputHint|StateHint|IconPixmapHint|IconWindowHint|
            IconPositionHint|IconMaskHint|WindowGroupHint|MessageHint|
            UrgencyHint)
WithdrawnState = 0
NormalState = 1
IconicState = 3
DontCareState = 0
ZoomState = 2
InactiveState = 4
RectangleOut = 0
RectangleIn = 1
RectanglePart = 2
VisualNoMask = 0x0
VisualIDMask = 0x1
VisualScreenMask = 0x2
VisualDepthMask = 0x4
VisualClassMask = 0x8
VisualRedMaskMask = 0x10
VisualGreenMaskMask = 0x20
VisualBlueMaskMask = 0x40
VisualColormapSizeMask = 0x80
VisualBitsPerRGBMask = 0x100
VisualAllMask = 0x1FF
ReleaseByFreeingColormap = 1
BitmapSuccess = 0
BitmapOpenFailed = 1
BitmapFileInvalid = 2
BitmapNoMemory = 3
XCSUCCESS = 0
XCNOMEM = 1
XCNOENT = 2


class _Window(command.CommandObject):
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        window.set_attribute(eventmask=self._windowMask)
        self.x, self.y, self.width, self.height = None, None, None, None
        self.borderwidth = 0
        self.bordercolor = None
        self.name = "<no name>"
        self.states = ["normal"]
        self.window_type = "normal"
        g = self.window.get_geometry()
        self.hints = {
            'input': True,
            'state': NormalState, #Normal state
            'icon_pixmap': None,
            'icon_window': None,
            'icon_x': 0,
            'icon_y': 0,
            'icon_mask': 0,
            'window_group': None,
            'urgent': False,
            }
        self.updateName()
        self.updateHints()

    def updateName(self):
        self.name = self.window.get_name()
        hook.fire("window_name_change")

    def updateHints(self):
        ''' 
          update the local copy of the window's WM_HINTS
          http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        '''
        h = self.window.get_wm_hints()
        # FIXME
        return

    @property
    def urgent(self):
        return self.hints['urgent']

    def info(self):
        return dict(
            name = self.name,
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            id = self.window.wid,
        )

    def setOpacity(self, opacity):
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xffffffff)
            self.window.set_property('_NET_WM_WINDOW_OPACITY', real_opacity)
        else:
            return

    def getOpacity(self):
        opacity = self.window.get_property(
            self.qtile.display.get_atom('_NET_WM_WINDOW_OPACITY'),
            Xatom.CARDINAL,
            0,
            32
            )
        if not opacity:
            return 1.0
        else:
            value = opacity.value[0]
            as_float = round(
                (float(value)/0xffffffff),
                2  #2 decimal places
                )
            return as_float

    opacity = property(getOpacity, setOpacity)

    def notify(self):
        # Having to do it this way is goddamn awful.
        vals = [
            22, # ConfigureNotifyEvent
            0,
            self.window.wid,
            self.window.wid,
            xcb.xproto.Window._None,
            self.x,
            self.y,
            self.width,
            self.height,
            self.borderwidth,
            False
        ]
        self.window.send_event(
            struct.pack(
                'B1xHLLLhhHHHB5x',
                *vals
            ),
            xcb.xproto.EventMask.StructureNotify
        )

    def kill(self):
        if "WM_DELETE_WINDOW" in self.window.get_wm_protocols():
            #e = event.ClientMessage(
            #        window = self.window,
            #        client_type = self.qtile.display.intern_atom("WM_PROTOCOLS"),
            #        data = [
            #            # Use 32-bit format:
            #            32,
            #            # Must be exactly 20 bytes long:
            #            [
            #                self.qtile.display.intern_atom("WM_DELETE_WINDOW"),
            #                X.CurrentTime,
            #                0,
            #                0,
            #                0
            #            ]
            #        ]
            #)
            vals = [
                33, # ClientMessageEvent
                32, # Format
                0,
                self.window.wid,
                self.qtile.conn.atoms["WM_PROTOCOLS"],
                self.qtile.conn.atoms["WM_DELETE_WINDOW"],
                xcb.xproto.Time.CurrentTime,
                0,
                0,
                0,
            ]
            e = struct.pack('BBHII5I', *vals)
            self.window.send_event(e)
        else:
            self.window.kill_client()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        self.disableMask(xcb.xproto.EventMask.StructureNotify)
        self.window.unmap()
        self.resetMask()
        self.hidden = True

    def unhide(self):
        self.window.map()
        self.hidden = False

    def disableMask(self, mask):
        self.window.set_attribute(
            eventmask=self._windowMask&(~mask)
        )

    def resetMask(self):
        self.window.set_attribute(
            eventmask=self._windowMask
        )

    def place(self, x, y, width, height, borderwidth, bordercolor):
        """
            Places the window at the specified location with the given size.
        """
        self.x, self.y, self.width, self.height = x, y, width, height
        self.borderwidth, self.bordercolor = borderwidth, bordercolor
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height,
            borderwidth=borderwidth
        )
        if bordercolor is not None:
            self.window.set_attribute(
                borderpixel = bordercolor
            )

    def focus(self, warp):
        if not self.hidden and self.hints['input']:
            self.window.set_input_focus()
            if warp:
                self.window.warp_pointer(0, 0)
        hook.fire("client_focus", self)

    def _items(self, name, sel):
        return None

    def _select(self, name, sel):
        return None

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return self.info()

    def cmd_inspect(self):
        """
            Tells you more than you ever wanted to know about a window.
        """
        a = self.window.get_attributes()
        attrs = {
            "backing_store": a.backing_store,
            "visual": a.visual,
            "class": a._class,
            "bit_gravity": a.bit_gravity,
            "win_gravity": a.win_gravity,
            "backing_planes": a.backing_planes,
            "backing_pixel": a.backing_pixel,
            "save_under": a.save_under,
            "map_is_installed": a.map_is_installed,
            "map_state": a.map_state,
            "override_redirect": a.override_redirect,
            #"colormap": a.colormap,
            "all_event_masks": a.all_event_masks,
            "your_event_mask": a.your_event_mask,
            "do_not_propagate_mask": a.do_not_propagate_mask
        }
        props = self.window.list_properties()
        normalhints = self.window.get_wm_normal_hints()
        hints = self.window.get_wm_hints()
        protocols = []
        for i in self.window.get_wm_protocols():
            protocols.append(i)

        state = self.window.get_wm_state()

        return dict(
            attributes=attrs,
            properties=props,
            name = self.window.get_name(),
            wm_class = self.window.get_wm_class(),
            wm_transient_for = self.window.get_wm_transient_for(),
            protocols = protocols,
            wm_icon_name = self.window.get_wm_icon_name(),
            wm_client_machine = self.window.get_wm_client_machine(),
            normalhints = normalhints,
            hints = hints,
            state = state
        )


class Internal(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange |\
                  EventMask.Exposure |\
                  EventMask.ButtonPress
    @classmethod
    def create(klass, qtile, x, y, width, height, opacity=1.0):
        win = qtile.conn.create_window(
                    x, y, width, height
              )
        win.set_property("QTILE_INTERNAL", 1)
        i = Internal(win, qtile)
        i.place(x, y, width, height, 0, None)
        i.opacity = opacity
        return i

    def __repr__(self):
        return "Internal(%s)"%self.name


class Static(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange |\
                  EventMask.Exposure
    def __init__(self, win, qtile, screen, x, y, width, height):
        _Window.__init__(self, win, qtile)
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.screen = screen
        self.place(x, y, width, height, 0, 0)

    def __repr__(self):
        return "Static(%s)"%self.name


class Window(_Window):
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange
    # Set when this object is being retired.
    defunct = False
    group = None
    def static(self, screen, x, y, width, height):
        """
            Makes this window a static window, attached to a Screen.
        """
        self.defunct = True
        screen = self.qtile.screens[screen]
        if self.group:
            self.group.remove(self)
        s = Static(self.window, self.qtile, screen, x, y, width, height)
        self.qtile.windowMap[self.window.wid] = self
        return s

    def handle_EnterNotify(self, e):
        hook.fire("client_mouse_enter", self)
        if self.group.currentWindow != self:
            self.group.focus(self, False)
        if self.group.screen and self.qtile.currentScreen != self.group.screen:
            self.qtile.toScreen(self.group.screen.index)
        return True

    def handle_ConfigureRequest(self, e):
        cw = xcb.xproto.ConfigWindow
        if e.value_mask & cw.X:
            self.x = e.x
        if e.value_mask & cw.Y:
            self.y = e.y
        if e.value_mask & cw.Width:
            self.width = e.width
        if e.value_mask & cw.Height:
            self.height = e.height
        self.place(self.x, self.y, self.width, self.height, self.borderwidth, self.bordercolor)
        self.notify()
        return False

    def handle_PropertyNotify(self, e):
        name = self.qtile.conn.atoms.get_name(e.atom)
        if name == "WM_TRANSIENT_FOR":
            pass
        elif name == "WM_HINTS":
            self.updateHints()
        elif name == "WM_NORMAL_HINTS":
            pass
        elif name == "WM_NAME":
            self.updateName()
        elif name == "_NET_WM_NAME":
            self.updateName()
        elif name == "_NET_WM_VISIBLE_NAME":
            self.updateName()
        elif name == "_NET_WM_WINDOW_OPACITY":
            pass
        elif name == "WM_PROTOCOLS":
            pass
        else:
            print >> sys.stderr, "Unknown window property: ", name
        return False

    def _items(self, name):
        if name == "group":
            return True, None
        elif name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "screen":
            return self.group.screen

    def __repr__(self):
        return "Window(%s)"%self.name

    def cmd_static(self, screen, x, y, width, height):
        self.static(screen, x, y, width, height)

    def cmd_kill(self):
        """
            Kill this window. Try to do this politely if the client support
            this, otherwise be brutal.
        """
        self.kill()

    def cmd_togroup(self, groupName):
        """
            Move window to a specified group.

            Examples:

                togroup("a")
        """
        group = self.qtile.groupMap.get(groupName)
        if group is None:
            raise command.CommandError("No such group: %s"%groupName)
        if self.group is not group:
            self.hide()
            self.group.remove(self)
            group.add(self)
            self.group.layoutAll()
            group.layoutAll()

    def cmd_opacity(self, opacity):
        self.opacity = opacity

