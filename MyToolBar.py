from matplotlib.backends.backend_qt5agg import  FigureCanvas, NavigationToolbar2QT
from PyQt5 import QtGui, QtCore,QtWidgets

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
    def __init__(self, canvas, parent, coordinates=True):
        NavigationToolbar2QT.__init__(self, canvas, parent, coordinates)
        self.fig_ratio = None

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