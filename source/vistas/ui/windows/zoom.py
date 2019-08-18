from matplotlib.patches import Rectangle


class Zoom:
    def __init__(self):
        # Global variables
        self.zoom_box_enabled = False  # User can draw a box if True
        self.mouse_in_bounds = True  # False if mouse was out of bounds
        self.draw_zoom_box = False  # True if the zoom box should be drawn
        self.zoom_disable_value = 48  # User will be unable to draw a box if zoomed in past this value

        self.zoom_x_diff = 0
        self.zoom_y_diff = 0

        # User bounds
        self.x_min = None
        self.x_max = None
        self.y_min = None
        self.y_max = None

        # Mouse initial position
        self.mouse_x = 0
        self.mouse_y = 0

        # Mouse drag distance
        self.mouse_x_diff = 0
        self.mouse_y_diff = 0

        # Current bounds of the graph
        self.x_hi = 0
        self.x_lo = 0
        self.y_hi = 0
        self.y_lo = 0

        # Center of the viewport
        self.center_x = 0
        self.center_y = 0

        # Absolute bounds of the graph
        self.x_lo_absolute = 0
        self.x_hi_absolute = 0
        self.y_lo_absolute = 0
        self.y_hi_absolute = 0

        # Square for user drawn box
        self.square = Rectangle((0, 0), 1, 1, alpha=0.3, color='red')

    def zoom_box_drawing_enabled(self):
        self.zoom_box_enabled = True
        self.draw_zoom_box = True

    def zoom_box_drawing_disabled(self):
        self.zoom_box_enabled = False
        self.draw_zoom_box = False

    def check_none(self, event_x, event_y):
        """Check if mouse coordinates are outside of the graph bounds"""
        if event_x is None:
            return False
        if event_y is None:
            return False
        return True

    def set_bounds_absolute(self, x_lo, x_hi, y_lo, y_hi):
        self.x_lo_absolute = x_lo
        self.x_hi_absolute = x_hi
        self.y_lo_absolute = y_lo
        self.y_hi_absolute = y_hi

    def get_bounds_absolute(self):
        return self.x_lo_absolute, self.x_hi_absolute, self.y_lo_absolute, self.y_hi_absolute

    def set_mouse_diff(self, event_x, event_y):
        if self.check_none(event_x, event_y) and self.mouse_in_bounds:
            self.mouse_x_diff = event_x - self.mouse_x
            self.mouse_y_diff = event_y - self.mouse_y

    def set_mouse_diff_zero(self):
        self.mouse_x_diff = 0
        self.mouse_y_diff = 0

    def set_mouse_initial(self, event_x, event_y):
        if self.check_none(event_x, event_y):
            self.mouse_x = event_x
            self.mouse_y = event_y
            self.mouse_in_bounds = True
        else:
            self.mouse_in_bounds = False

    def mouse_release(self, event_x, event_y):
        self.set_mouse_diff(event_x, event_y)
        self.draw_zoom_box = False

    def reset_zoom(self, x_min, x_max, y_min, y_max):
        """Reset the zoom controls and graph bounds"""
        self.zoom_box_enabled = False

        # Save bound variables
        self.x_lo = x_min
        self.x_hi = x_max
        self.y_lo = y_min
        self.y_hi = y_max

        # Calculate center point
        self.center_x = x_min + (x_max - x_min) / 2
        self.center_y = y_min + (y_max - y_min) / 2

        # self.zoom_update = False
        # self.zoom_x = 0
        # self.zoom_y = 0
        #
        # self.zoom_value_last = 0
        #
        # self.zoom_x_or_y = True

        self.zoom_x_diff = 0
        self.zoom_y_diff = 0

    def calculate_zoom(self, x_min, x_max, y_min, y_max, zoom_level_current):
        """Calculate the bounds of the graph when 'Zoom' axis type is selected"""

        # Current boundaries will be kept
        keep_bounds = True

        # Variables to return
        draw_box = False
        zoom_level_final = zoom_level_current

        # Size of boundaries
        x_length = (x_max - x_min)
        y_length = (y_max - y_min)

        # Divide sides for percentages
        x_ticks = x_length / 100
        y_ticks = y_length / 100

        # Set initial values
        x_lo = self.x_lo
        x_hi = self.x_hi
        y_lo = self.y_lo
        y_hi = self.y_hi
        zoom_amt_x = 0
        zoom_amt_y = 0

        # User drawn box to zoom in to
        if self.zoom_box_enabled:

            # The length of the zoomed in bounds
            x_length_current = abs(self.x_hi - self.x_lo)
            y_length_current = abs(self.y_hi - self.y_lo)

            # Percentage of the total bounds covered
            x_percentage = self.mouse_x_diff / x_length_current
            y_percentage = self.mouse_y_diff / y_length_current

            # Figure out smallest side of rectangle
            if abs(x_percentage) <= abs(y_percentage):
                zoom_value = ((x_length - abs(self.mouse_x_diff)) / 2) / x_ticks
                # x_box = (x_length_current * abs(x_percentage)) / 2
                # y_box = (y_length_current * abs(x_percentage)) / 2
            else:
                zoom_value = ((y_length - abs(self.mouse_y_diff)) / 2) / y_ticks
                # x_box = (x_length_current * abs(y_percentage)) / 2
                # y_box = (y_length_current * abs(y_percentage)) / 2

            x_box = abs(self.mouse_x_diff)
            y_box = abs(self.mouse_y_diff)

            # Drawing a box on the graph
            if self.draw_zoom_box:
                draw_box = True

                # Set length of box sides
                self.square.set_width(x_box)
                self.square.set_height(y_box)

                # Draw corner of box depending on which direction the user is dragging
                if (x_percentage >= 0) and (y_percentage >= 0):
                    self.square.set_xy((self.mouse_x, self.mouse_y))
                elif (x_percentage <= 0) and (y_percentage >= 0):
                    self.square.set_xy((self.mouse_x - x_box, self.mouse_y))
                elif (x_percentage <= 0) and (y_percentage <= 0):
                    self.square.set_xy((self.mouse_x - x_box, self.mouse_y - y_box))
                else:
                    self.square.set_xy((self.mouse_x, self.mouse_y - y_box))

            # Zooming into a drawn box
            elif zoom_value < 50 and self.mouse_in_bounds:

                # Figure out if the width or height is largest of the user's rectangle
                if abs(x_percentage) <= abs(y_percentage):
                    zoom_value = round(((x_length - abs(self.mouse_x_diff)) / 2) / x_ticks)
                    zoom_2 = round(((y_length - abs(self.mouse_y_diff)) / 2) / y_ticks)
                    self.zoom_x_diff = 0
                    self.zoom_y_diff = zoom_value - zoom_2
                else:
                    zoom_value = round(((y_length - abs(self.mouse_y_diff)) / 2) / y_ticks)
                    zoom_2 = round(((x_length - abs(self.mouse_x_diff)) / 2) / x_ticks)
                    self.zoom_y_diff = 0
                    self.zoom_x_diff = zoom_value - zoom_2

                zoom_level_final = zoom_value

                if (x_percentage >= 0) and (y_percentage >= 0):
                    x_lo = self.mouse_x
                    y_lo = self.mouse_y
                elif (x_percentage <= 0) and (y_percentage >= 0):
                    x_lo = self.mouse_x - x_box
                    y_lo = self.mouse_y
                elif (x_percentage <= 0) and (y_percentage <= 0):
                    x_lo = self.mouse_x - x_box
                    y_lo = self.mouse_y - y_box
                else:
                    x_lo = self.mouse_x
                    y_lo = self.mouse_y - y_box

                zoom_amt_x = (zoom_level_final-self.zoom_x_diff) * x_ticks
                zoom_amt_y = (zoom_level_final-self.zoom_y_diff) * y_ticks

                x_hi = x_lo + (x_length - 2 * zoom_amt_x)

                y_hi = y_lo + (y_length - 2 * zoom_amt_y)

                self.center_x = x_lo + (x_length / 2 - zoom_amt_x)
                self.center_y = y_lo + (y_length / 2 - zoom_amt_y)

                keep_bounds = False

            self.zoom_box_enabled = self.draw_zoom_box

        else:
            # Slows down shifting for the user
            shift_amt = -1.5  # Sign is flipped or dragging will move opposite of what is expected

            # Distance user dragged across screen to shift viewport
            shift_x = self.mouse_x_diff / shift_amt
            shift_y = self.mouse_y_diff / shift_amt

            # Amount to zoom in by based on the value of the slider
            if (zoom_level_current-self.zoom_x_diff) < 0:
                self.zoom_x_diff += zoom_level_current-self.zoom_x_diff
                #print("X OVER ", zoom_level_current-self.zoom_x_diff)
            if (zoom_level_current-self.zoom_y_diff) < 0:
                self.zoom_y_diff += zoom_level_current - self.zoom_y_diff
                #print("Y OVER ", zoom_level_current - self.zoom_y_diff)

            zoom_amt_x = (zoom_level_current-self.zoom_x_diff) * x_ticks
            zoom_amt_y = (zoom_level_current-self.zoom_y_diff) * y_ticks

            # Shift the center by the amount user dragged
            self.center_x += shift_x
            self.center_y += shift_y

            # Calculate bounds based on center and zoom amount

            x_lo = self.center_x - (x_length / 2 - zoom_amt_x)
            x_hi = self.center_x + (x_length / 2 - zoom_amt_x)

            y_lo = self.center_y - (y_length / 2 - zoom_amt_y)
            y_hi = self.center_y + (y_length / 2 - zoom_amt_y)

            keep_bounds = False

        if keep_bounds:
            # Keep current bounds
            return self.x_lo, self.x_hi, self.y_lo, self.y_hi, draw_box, zoom_level_final
        else:
            # Check if new bounds are within absolute bounds

            # X axis
            if x_lo < x_min:
                x_lo = x_min
                x_hi = x_max - (2 * zoom_amt_x)
                self.center_x = x_min + (x_length / 2 - zoom_amt_x)
            if x_hi > x_max:
                x_hi = x_max
                x_lo = x_min + (2 * zoom_amt_x)
                self.center_x = x_max - (x_length / 2 - zoom_amt_x)

            # Y axis
            if y_lo < y_min:
                y_lo = y_min
                y_hi = y_max - (2 * zoom_amt_y)
                self.center_y = y_min + (y_length / 2 - zoom_amt_y)
            if y_hi > y_max:
                y_hi = y_max
                y_lo = y_min + (2 * zoom_amt_y)
                self.center_y = y_max - (y_length / 2 - zoom_amt_y)

            # Record bounds for later use
            self.x_lo = x_lo
            self.x_hi = x_hi
            self.y_lo = y_lo
            self.y_hi = y_hi

            # Set new bounds
            # print("ZOOM LEVEL", zoom_level_final, "Zoom X", zoom_level_final-self.zoom_x_diff, "Zoom Y",
                  # zoom_level_final-self.zoom_y_diff)
            return x_lo, x_hi, y_lo, y_hi, draw_box, zoom_level_final

    def calculate_zoom_user(self, x_min, x_max, y_min, y_max, user_x_min, user_x_max, user_y_min, user_y_max):

        # Size of boundaries
        x_length = (x_max - x_min)
        y_length = (y_max - y_min)

        # Divide sides for percentages
        x_ticks = x_length / 100
        y_ticks = y_length / 100

        # Set initial values
        x_lo = user_x_min
        x_hi = user_x_max
        y_lo = user_y_min
        y_hi = user_y_max

        if (user_x_min >= user_x_max):
            x_lo = x_min
            x_hi = x_max
        elif (user_x_min < x_min):
            x_lo = x_min
        elif (user_x_max > x_max):
            x_hi = x_max

        if (user_y_min >= user_y_max):
            y_lo = y_min
            y_hi = y_max
        elif (user_y_min < y_min):
            y_lo = y_min
        elif (user_y_max > y_max):
            y_hi = y_max

        # Percentage of the total bounds covered
        x_percentage = (x_hi-x_lo) / x_length
        y_percentage = (y_hi-y_lo) / y_length

        # Figure out if the width or height is largest of the user's rectangle
        if abs(x_percentage) <= abs(y_percentage):
            zoom_value = round(((x_length - abs(x_hi-x_lo)) / 2) / x_ticks)
            zoom_2 = round(((y_length - abs(y_hi-y_lo)) / 2) / y_ticks)
            self.zoom_x_diff = 0
            self.zoom_y_diff = zoom_value - zoom_2
        else:
            zoom_value = round(((y_length - abs(y_hi-y_lo)) / 2) / y_ticks)
            zoom_2 = round(((x_length - abs(x_hi-x_lo)) / 2) / x_ticks)
            self.zoom_y_diff = 0
            self.zoom_x_diff = zoom_value - zoom_2

        zoom_level_final = zoom_value

        zoom_amt_x = (zoom_level_final - self.zoom_x_diff) * x_ticks
        zoom_amt_y = (zoom_level_final - self.zoom_y_diff) * y_ticks

        self.center_x = x_lo + (x_length / 2 - zoom_amt_x)
        self.center_y = y_lo + (y_length / 2 - zoom_amt_y)

        # Record bounds for later use
        self.x_lo = x_lo
        self.x_hi = x_hi
        self.y_lo = y_lo
        self.y_hi = y_hi

        return x_lo, x_hi, y_lo, y_hi, False, zoom_level_final