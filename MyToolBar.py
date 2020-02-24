from matplotlib.backend_tools import ToolBase, ToolToggleBase
import matplotlib.lines as lines
import matplotlib.text as text
import math, os
from matplotlib.backends.backend_qt5agg import  FigureCanvas, NavigationToolbar2QT
from PyQt5 import QtGui, QtCore,QtWidgets
from datetime import datetime

def keepRatio(xmin, xmax, ymin, ymax, fig_ratio, bigger = True):
    ax_ratio = (xmax - xmin)/(ymax - ymin)
    spanx = xmax - xmin 
    xmid = (xmax+xmin)/2
    spany = ymax - ymin
    ymid = (ymax+ymin)/2
    if bigger:
        if ax_ratio > fig_ratio:
            ymax = ymid + spany*ax_ratio/fig_ratio/2
            ymin = ymid - spany*ax_ratio/fig_ratio/2
        elif ax_ratio < fig_ratio:
            xmax = xmid + spanx*fig_ratio/ax_ratio/2
            xmin = xmid - spanx*fig_ratio/ax_ratio/2
    else:
        if ax_ratio < fig_ratio:
            ymax = ymid + spany*ax_ratio/fig_ratio/2
            ymin = ymid - spany*ax_ratio/fig_ratio/2
        elif ax_ratio > fig_ratio:
            xmax = xmid + spanx*fig_ratio/ax_ratio/2
            xmin = xmid - spanx*fig_ratio/ax_ratio/2
    return xmin, xmax, ymin ,ymax

class MyToolBar(NavigationToolbar2QT):
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        ('Measure', 'Measure distance', 'images/ruler','ruler'),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
        (None, None, None, None),
      )
    def __init__(self, canvas, parent, ruler, coordinates=True):
        NavigationToolbar2QT.__init__(self, canvas, parent, coordinates)
        self.fig_ratio = None
        self._ruler = ruler
        self._rulerXY = []

    def release_zoom(self, event):
        """Callback for mouse button release in zoom to rect mode."""
        for zoom_id in self._ids_zoom:
            self.canvas.mpl_disconnect(zoom_id)
        self._ids_zoom = []

        self.remove_rubberband()

        if not self._xypress:
            return

        last_a = []

        for cur_xypress in self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, ind, view = cur_xypress
            # ignore singular clicks - 5 pixels is a threshold
            # allows the user to "cancel" a zoom action
            # by zooming by less than 5 pixels
            if ((abs(x - lastx) < 5 and self._zoom_mode!="y") or
                    (abs(y - lasty) < 5 and self._zoom_mode!="x")):
                self._xypress = None
                self.release(event)
                self.draw()
                return

            # detect twinx,y axes and avoid double zooming
            twinx, twiny = False, False
            if last_a:
                for la in last_a:
                    if a.get_shared_x_axes().joined(a, la):
                        twinx = True
                    if a.get_shared_y_axes().joined(a, la):
                        twiny = True
            last_a.append(a)

            if self._button_pressed == 1:
                direction = 'in'
            elif self._button_pressed == 3:
                direction = 'out'
            else:
                continue
            if self.fig_ratio != None:
                (lastx, x, lasty, y) = keepRatio(lastx, x, lasty, y, self.fig_ratio)
            a._set_view_from_bbox((lastx, lasty, x, y), direction,
                                self._zoom_mode, twinx, twiny)
        self.draw()
        self._xypress = None
        self._button_pressed = None

        self._zoom_mode = None

        self.push_current()
        self.release(event)

    def _init_toolbar(self):
        super()._init_toolbar()
        self._actions['ruler'].setCheckable(True)

    def _icon(self, name):
        name = name.replace('.png', '_large.png')
        filename = os.path.join(self.basedir, name)
        if os.path.exists(filename):
            pm = QtGui.QPixmap(filename)
        else:
            cur_dir = os.getcwd()
            pm = QtGui.QPixmap(cur_dir+'/'+name)
        if hasattr(pm, 'setDevicePixelRatio'):
            pm.setDevicePixelRatio(self.canvas._dpi_ratio)
        return QtGui.QIcon(pm)

    def _update_buttons_checked(self):
        # sync button checkstates to match active mode
        self._actions['pan'].setChecked(self._active == 'PAN')
        self._actions['zoom'].setChecked(self._active == 'ZOOM')
        self._actions['ruler'].setChecked(self._active == 'RULER')

    def pan(self, *args):
        super().pan(*args)
        self._update_buttons_checked()

    def zoom(self, *args):
        super().zoom(*args)
        self._update_buttons_checked()

    def ruler(self):
        """Activate ruler."""
        if self._active == 'RULER':
            self._active = None
        else:
            self._active = 'RULER'

        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''

        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''

        if self._active:
            self._idPress = self.canvas.mpl_connect('button_press_event',
                                                    self.press_ruler)
            self._idRelease = self.canvas.mpl_connect('button_release_event',
                                                      self.release_ruler)
            self.mode = 'measuring'
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)
            self._ruler.hide_all()
            self.canvas.figure.canvas.draw()

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self.set_message(self.mode)
        self._update_buttons_checked()

    def press_ruler(self, event):
        """Callback for mouse button press in Ruler mode."""
        if event.button == 1 and event.inaxes:
            self._button_pressed = 1
        else:
            self._button_pressed = None
            return
        self._rulerXY = [[event.xdata, event.ydata],[event.xdata, event.ydata]]
        if self._idDrag is not None:
            self._idDrag = self.canvas.mpl_disconnect(self._idDrag)
        self._idDrag = self.canvas.mpl_connect('motion_notify_event', self.move_ruler)
        self._ruler.update(event.inaxes, self._rulerXY)
        self._ruler.set_visible(event.inaxes, True)

    def release_ruler(self, event):
        """Callback for mouse button release in Ruler mode."""
        if event.button == 1 and event.inaxes:
            self._button_pressed = 1
        else:
            self._button_pressed = None
            return
        if self._idDrag is not None:
            self._idDrag = self.canvas.mpl_disconnect(self._idDrag)

    def move_ruler(self, event):
        """Callback for mouse button move in Ruler mode."""
        if event.button == 1 and event.inaxes:
            self._button_pressed = 1
        else:
            self._button_pressed = None
            return
        self._rulerXY[1] = [event.xdata, event.ydata]
        self._ruler.update(event.inaxes, self._rulerXY)
        self.canvas.figure.canvas.draw()

class RulerShape:
    def __init__(self):
        self._lines = []
        self._texts = []
        self._axs = []
    
    def clear_rulers(self):
        self._lines = []
        self._texts = []
        self._axs = []

    def add_ruler(self,ax):
        ruler_t = text.Text(0, 0, '')
        ruler_t.set_bbox(dict(facecolor='white', alpha=0.5))
        ruler_l = lines.Line2D([],[], marker = '+', linestyle = '-', color = 'black', markersize = 10.0)
        ruler_t.set_visible(False)
        ruler_l.set_visible(False)
        ruler_l.set_zorder(101)
        ruler_t.set_zorder(100)
        ax.add_line(ruler_l)
        ax.add_artist(ruler_t)
        if ax not in self._axs:
            self._lines.append(ruler_l)
            self._texts.append(ruler_t)
            self._axs.append(ax)
        else:
            indx = self._axs.index(ax)
            self._lines[indx] = ruler_l
            self._texts[indx] = ruler_t
        
    def update(self, ax, data):
        indx = self._axs.index(ax)
        self._lines[indx].set_xdata([data[0][0],data[1][0]])
        self._lines[indx].set_ydata([data[0][1],data[1][1]])
        self._texts[indx].set_x(data[1][0])
        self._texts[indx].set_y(data[1][1])
        dx = data[1][0] - data[0][0]
        dy = data[1][1] - data[0][1]
        ds = math.sqrt(dx * dx + dy * dy)
        self._texts[indx].set_text('X:{:.3f} m\nY:{:.3f} m\nD:{:.3f} m'.format(dx, dy, ds))

    def set_visible(self, ax, value):
        indx = self._axs.index(ax)
        self._texts[indx].set_visible(value)
        self._lines[indx].set_visible(value)

    def hide_all(self):
        for t,l in zip(self._texts, self._lines):
            t.set_visible(False)
            l.set_visible(False)

class RulerShapeMap(RulerShape):
    def __init__(self):
        super(RulerShapeMap, self).__init__()

    def update(self, ax, data):
        indx = self._axs.index(ax)
        self._lines[indx].set_xdata([data[0][0],data[1][0]])
        self._lines[indx].set_ydata([data[0][1],data[1][1]])
        self._texts[indx].set_x(data[1][0])
        self._texts[indx].set_y(data[1][1])
        t1 = datetime.fromtimestamp(data[1][0] * 86400 - 62135712000)
        t0 = datetime.fromtimestamp(data[0][0] * 86400 - 62135712000)
        dt = (t1 - t0).total_seconds()
        dy = data[1][1] - data[0][1]
        self._texts[indx].set_text('dY:{:.3e}\ndT:{:.3e} s'.format(dy, dt))