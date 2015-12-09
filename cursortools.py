#!usr/bin/env python
# -*- coding: utf-8 -*-

"""Cursor tools module.

Provides draggable cursors in matplotlib axes.

TODO
----
[X] New cursors can be interactively added to the current axes by clicking the
    middle mouse button.

clemens.reiffurth@gmail.com (2015)
"""

from __future__ import print_function, division  
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.transforms as transforms
import pandas as pd
import re
import sys
import ipdb


def setcursormode(cur_mode, cursors='all', ax='current'):
    """Set cursor interaction mode of a selection of cursors.

    Parameters
    ----------
    cur_mode : String
        Cursor interaction mode (interact|fixed).
    cursors : Int|Sequence
        Selection of cursors. IDs (integers), or cursor objects.

    Example
    -------
    # change the cursor mode for a range (2,3,4,5) of cursors in plot
    >>> ct.setcursormode('fixed', range(2,6))

    """
    if ax == 'current':
        ax = plt.gca()

    cur_objs = [] # cursor objects
    if isinstance(cursors, (int, long)): # single ID (int)
        cursors = [cursors]
    
    if cursors == 'all': # default
        cur_objs = ax.curlist
    # Sequence of integers
    elif hasattr(cursors, '__len__') and isinstance(cursors[0], (int, long)):
        for ii in cursors: # cursor IDs (int)
            for cj in ax.curlist:
                if ii == cj.get_id():
                    cur_objs.append(cj)
    # Set the cursor mode    
    for ci in cur_objs:
        ci.set_mode(cur_mode)

    
def savecurinfo(ax='current', filename='curinfo.csv'):
    """Save cursor and span information from plot to CSV file.

    Enable recreating all cursors and spans whith same positions and
    features in a plot. Allow for scripts to use cursor information to
    process associated data.

    PARAMETERS
    ----------
    ax : matplotlib.axes
        Axes object
    filename : String
        Filename of file with cursor information.
    """
    if ax == 'current':
        ax = plt.gca()

    # Cursor properties with explanation
    prop_expl = {'xpos':'x-axis position',
                 'color':'cursor line and text color',
                 'tag':'entire cursor name string including ID',
                 'id':'cursor ID: unique integer in parentheses',
                 'type':'cursor type (vertical|vertspan)',
                 'mode':'mode of cursor interactivity (interact|fixed)'}

    cur_prop_df = pd.DataFrame() # initialize empty DataFrame
    for ci in ax.curlist:
        # Collect cursor properties
        cur_props = {'xpos':ci.get_xpos(),
                     'color':ci.get_color(),
                     'tag':ci.get_tag(),
                     'id':ci.get_id(),
                     'type':ci.orient,
                     'mode':ci.mode}
        cur_prop_df = cur_prop_df.append(cur_props, ignore_index=True)
        
    # Adjust DataFrame column order and sort by cursor ID
    col_order = ['id', 'tag', 'xpos', 'type', 'mode', 'color']
    cur_prop_df = cur_prop_df[col_order].sort(columns='id')
    cur_prop_df.to_csv(filename, index=False) # Save to CSV
    return cur_prop_df


def loadcurinfo(ax='current', filename='curinfo.csv'):
    """Load cursor and span information from file and recreate them in plot.

    Enable recreating all cursors and spans whith same positions and
    features in a plot.

    PARAMETERS
    ----------
    ax : matplotlib.axes
        Axes object
    filename : String
        Filename of CSV file with cursor information.
    """
    if ax == 'current':
        ax = plt.gca()
        
    cur_df = pd.read_csv(filename) # load cursor info from CSV file

    def initcur(cur_obj, row):
        """Initialize cursor with given parameters.
        """
        cur_obj.set_mode(row['mode'])
        cur_obj.set_color(row['color'])
        cur_obj.set_tag(row['tag'])
        return cur_obj

    last_row = pd.Series()
    for index, row in cur_df.iterrows():
        cur_type = row['type']
        # Cursors
        if row['type'] == 'vertical':
            cur_obj = placecursor(ax, pos=row['xpos'])
            initcur(cur_obj, row)
        # Spans
        elif cur_type == 'vertspan':
            if last_row.empty: # we need parameters for both cursors
                last_row = row
            else:
                low_cur = last_row['xpos']
                high_cur = row['xpos']
                span_obj = placespan(ax, pos=(low_cur, high_cur))
                span_obj.set_color(row['color'])
                initcur(span_obj.span_low, last_row)
                initcur(span_obj.span_high, row)
                last_row = pd.Series()

    return cur_df

    
def getcurpos(ax, sub_str):
    """Collect cursor positions on the basis of the cursor tag.
    """
    cur_pos = []
    for ci in ax.curlist:
        if sub_str in ci.tag.get_text():
            cur_pos.append(ci.cline._xy[0][0]) # x axisi value only
    return cur_pos


def getallcurpos(ax='current'):
    """Get all cursor positions on the x axis.

    Parameters
    ----------
    ax (matplotlib.axes.Axes): Axes object; defaults to current axes.

    Returns
    -------
    curpos (array-like): Vector with all x or y positions of cursors in current
        axes.
    """
    if ax == 'current':
        ax = plt.gca()
    curpos = np.array([])
    for ci in ax.curlist:
        curpos = np.append(curpos, ci.cline.get_xdata())
    
    return curpos

    
def spanonclick(ax='current'):
    """Interactively add span to current axes using the mouse.

    Press the middle mouse button to add a cursor span at the mouse pointer
    location.
    """
    # Get current axes
    if ax == 'current':
        ax = plt.gca()
        fig = ax.get_figure()
    # Disconnect from previous callbacks
    if hasattr(fig, 'cidpress'):
        fig.canvas.mpl_disconnect(fig.cidpress)

    def onclick(event):
        """Callback function.
        """
        if event.inaxes:
            if event.button == 2:
                placespan(ax, pos=event.xdata)
                plt.show()

    # Connect callback function to event manager
    fig.cidpress = fig.canvas.mpl_connect('button_press_event', onclick)
    pass


def curonclick(ax='current'):
    """Interactively add cursor to current axes using the mouse.

    Press the middle mouse button to add a cursor at the mouse pointer location.
    """
    # Get current axes
    if ax == 'current':
        ax = plt.gca()
        fig = ax.get_figure()
    # Disconnect from any previous callbacks
    if hasattr(fig, 'cidpress'):
        fig.canvas.mpl_disconnect(fig.cidpress)

    def onclick(event):
        """Callback function.
        """
        if event.inaxes:
            if event.button == 2:
                placecursor(ax, pos=event.xdata)
                plt.show()

    # Connect callback function to event manager
    fig.cidpress = fig.canvas.mpl_connect('button_press_event', onclick)


def getcur(cur_id, ax='current'):
    """Return cursor object based on ID.

    PARAMETERS
    ----------
    ax (matplotlib.axes.Axes): Axes object; defaults to current axes.
    cur_id (int): cursor idenfication number (ID).
    """
    if ax == 'current':
        ax = plt.gca()
    # Find cursor by means of its label
    for ci in ax.curlist:
        if cur_id == ci.get_id():
            return ci
    print("Cursor ID not found!")


def placecursor(ax, pos='center', **kwargs):
    """Place cursor in given axes with sensible defaults.

    Parameters
    ----------
    ax (matplotlib.axes.Axes): axes object; defaults to current axes
    pos (string|scalar): Defaults to center of axes

    **kwargs
    --------
    Input parameters for plt.axhline or plt.axvline (line objects).

    Returns
    -------
    cur (DragCursor object): Cursor object.

    """
    if pos == 'center':
        # Calculate cursor positions 
        axspan = ax.get_xlim()[1] - ax.get_xlim()[0] # total axis span
        pos = ax.get_xlim()[0] + axspan/2

    # Default cursor properties
    curprops = {'snap':True,
                'color':'r',
                'linewidth':1.2,
                'picker':10,
                'linestyle':'--'}

    # Update the properties with kwargs dict
    curprops.update(kwargs)
    dc = DragCursor(ax, pos, **curprops)

    return dc


def placespan(ax, pos='center', curprops={},
              spanprops={}, **kwargs):
    """Place cursor in given axes with sensible defaults.

    Parameters
    ----------
    ax (matplotlib.axes.Axes): axes object; defaults to current axes
    pos (string|scalar|sequence): Defaults to center of axes
    curprops (dict): User-defined cursor properties.
    spanprops (dict): User-defined span properties.

    Returns
    -------
    span (DragSpan object): Span object.

    Notes
    -----
    Right now only vertical cursors are supported.
    
    """
    if hasattr(pos, '__len__') and not isinstance(pos, basestring):
        low_pos = pos[0]
        high_pos = pos[1]
    else:
        # Calculate span cursors positions
        axspan = ax.get_xlim()[1] - ax.get_xlim()[0] # total axis span
        divfact = 6 # factor for scaling cursor positioning 
        limfrac = axspan/divfact # fraction
        if pos == 'center':
            axcenter = ax.get_xlim()[0] + axspan/2
            low_pos = axcenter - limfrac
            high_pos = axcenter + limfrac
        # We assume it is a number 
        else:
            low_pos = pos - limfrac/2
            high_pos = pos + limfrac/2
            
    
    # Default cursor properties
    curdefault = {'snap':True,
                  'color':'r',
                  'linewidth':1.2,
                  'picker':10,
                  'linestyle':'--'}

    # Default span properties
    spandefault = {'facecolor':'none',
                   'edgecolor':'r',
                   'alpha':0.2,
                   'linestyle':'dashed',
                   'hatch':'//\\\\'}
    curdefault.update(curprops)
    spandefault.update(spanprops)

    ds = DragSpan(ax, low_pos, high_pos,
                  curprops=curdefault,
                  spanprops=spandefault)
    return ds


def remcur(cur):
    """Remove cursor objects.
    """
    if not hasattr(cur, '__len__'):
        cursors = [cur]
    else:
        cursors = cur[:] # copy ax.curlist
    while cursors: # removal takes several passes(?)
        for ci in cursors:
            # Remove line and text objects
            ci.cline.remove() # line artist
            ci.tag.remove() # text artist
            ci.ax.curlist.remove(ci) # cursor object
            # Disconnect callbacks from event manager
            ci.cline.figure.canvas.mpl_disconnect(ci.cidpress)
            ci.cline.figure.canvas.mpl_disconnect(ci.cidrelease)
            ci.cline.figure.canvas.mpl_disconnect(ci.cidmotion)
            cursors.remove(ci)
    plt.show()


def initag(self):
    """Create initial unique tag for cursor objects and show text box.

    Cursor ID tags are simply integers shown in the box above the
    cursor. They serve as a means to identify and target the
    corresponding cursor to e.g. change its properties.

    """
    if self.orient == 'vertspan':
        obj_list = self.ax.spanlist
    elif self.orient == 'vertical':
        obj_list = self.ax.curlist
    else:
        print('Non supported cursor type: %s' %self.orient)
        return
    ID_list = []
    for ci in self.ax.curlist:
        try:
            # 'r' for Phython's raw string notation for regexps
            re_match = re.search(r'\((\d+)\)', ci.tag.get_text()) 
            # ID_str, = re.findall(r'\d+', ci.tag.get_text()) 
            ID_str = re_match.group(1)
            ID_list.append(int(ID_str))
        except ValueError: # no number found in string
            pass
            # print('DragCursor ID string cannot be converted to integer!')
        except AttributeError: # cursor has no tag
            pass
            # print('DragCursor object has no attribute "tag"!')
    ID_list.sort()
    if ID_list:
        # tagstr = max(ID_list) + 1
        tagstr = '(' + str((max(ID_list)+1)) + ')'
    else: # No tag string in list (yet) 
        tagstr = '(1)'

    # Blended coordinate spaces: Mix axes with data coordinates
    trans = transforms.blended_transform_factory(
        self.ax.transData, self.ax.transAxes) 
    bbox_props = dict(boxstyle='round, pad=0.3', fc='white', ec='black',
                lw=1, alpha=0.5)  
    self.tag = self.ax.text(self.cline.get_xdata()[0], 1.04, tagstr, 
                ha='center', va='center', size=12, color=self.color, 
                bbox=bbox_props, alpha=1, transform=trans) # cursor string 


def setcurtag(cur, new_str, ax='current', keep_id=True):
    """Assign names to cursors and spans.

    PARAMETERS
    ----------
    cur (number|string|cursor object): Cursor ID number, DragCursor
    instance or name string, e.g. '3'. Sequences of cursor objects or
    strings are also processed.
    new_str (string): New cursor name/ID.  keep_id (boolean): Whether
    the initial ID (integer) should be appended to the new
    string. Default is True.
    ax (matplotlib.axes): Axis that holds cursors of interest. Defaults
    to 'current'.

    TODO
    ----
    [ ] check for uniqueness of name

    Cursor ID tags are simply integers shown in the box above the
    cursor. They serve as a means to identify and target the
    corresponding cursor to e.g. change its properties.

    """
    if ax == 'current':
        ax = plt.gca()

    # What type is first input argument?
    if isinstance(cur, basestring): # string
        cur_obj_list = []
        for ci in ax.curlist:
            if cur == ci.tag.get_text():
                cur_obj_list.append(ci)
        if len(cur_obj_list) == 1:
            cur_obj = cur_obj_list[0]
        elif len(cur_obj_list) > 1:
            print('ID string is not unique: More than one match found!')
            return
        elif not cur_obj_list:
            print('String not found!')
            return
    elif isinstance(cur, (int, long)):
        print('Input argument is an integer!')
        for ci in ax.curlist:
            ci_tag = ci.tag.get_text()
            ci_match = re.search(r"\((\d+)\)", ci_tag)
            if ci_match:
                ci_num = int(ci_match.group(1))
                if cur == ci_num:
                    cur_obj = ci
                    print('Cursor found!')
                    print('String: %s' %ci.tag.get_text())
    elif isinstance(cur, DragCursor): # cursor object
        cur_obj = cur
    else:
        raise TypeError('Supply appropriate argument: DragCursor instance or string!')

    def setnewname(cur_obj, new_str, keep_id):
        """Set cursor text object according to new string.
        """
        old_str = cur_obj.tag.get_text()
        if keep_id: # IDs remain in new name
            # Find ID integers in cursor ID string
            str_match = re.search(r"\((\d+)\)", old_str)
            cur_id = str_match.group(0)
            new_str = new_str + cur_id
        cur_obj.tag.set_text(new_str)
    
    if cur_obj.orient == 'vertspan':
        setnewname(cur_obj.spanobj.span_low, new_str, keep_id)
        setnewname(cur_obj.spanobj.span_high, new_str, keep_id)
    elif cur_obj.orient == 'vertical':
        setnewname(cur_obj, new_str, keep_id)
    ax.get_figure().show()


class DragCursor(object):
    """Movable cursor.
    """
    def __init__(self, ax, pos, orient='vertical', mode='interact', **kwargs): 
        """Constructor.

        Parameters
        ----------
        ax (matplotlib.axes.Axes): current axes
        pos (scalar): x- or y-axis position
        orient (string): cursor orientation (vertical|vertspan)
        mode (string): Cursor interaction mode (interact|fixed).

        **kwargs
        --------
        Input parameters for plt.axhline or plt.axvline.

        Notes
        -----
        For now only single vertical cursors or vertical cursors as part of a
        span are supported.

        """
        # Attach cursor object list to axis
        if hasattr(ax, 'curlist'):
            ax.curlist.append(self)
        else:
            ax.curlist = [self]

        self._kwargs = kwargs
        self._press = None
        self.ax = ax
        self.ident = id(self) # object identity
        self.mode = mode # interaction mode (draggable or not)
        self.orient = orient # cursor direction 
        self.color = self._kwargs.get('color', 'r')
        # Create line
        if self.orient in ['vertical', 'vertspan']: # Vertical cursor
            self.cline = ax.axvline(pos, **kwargs) # cursor line
        initag(self) # Attach unique ID and text box
        self._connect() # Connect callbacks


    def set_mode(self, mode):
        """Set the cursor interaction mode.

        Parameters
        ----------
        mode (string): Interaction mode (interact|fixed).
        """
        self.mode = mode
        # Change linestyle according to mode
        if mode == 'interact':
            self.cline.set_ls(self._kwargs.get('linestyle', '--'))
        elif mode == 'fixed':
            self.cline.set_ls('-.')
        # Update figure
        self.ax.get_figure().show()
        

    def get_id(self):
        """Return the cursor ID.

        RETURNS
        -------
        cur_id (int): Cursor ID.
        """
        cur_tagstr = self.tag.get_text()
        match_str = re.search(r'\((\d+)\)', cur_tagstr)
        cur_id = int(match_str.group(1))
        return cur_id


    def get_text(self):
        """Return the cursor tag string including cursor ID.

        RETURNS
        -------
        cur_text (string): Cursor box string (tag + ID).
        """
        cur_text = self.tag.get_text()
        return cur_text


    def get_tag(self):
        """Return the cursor tag string omitting the cursor ID.

        The cursor tag string gives information about the cursor
        function.
        
        RETURNS
        -------
        cur_tag (string): Cursor tag string.

        """
        full_str = self.get_text()
        tag_str = re.sub(r'\(\d+\)', '', full_str)
        return tag_str


    def set_tag(self, tag_str):
        """Set the cursor tag.
        
        The cursor ID is preserved and appended to the cursor tag
        string. The cursor tag string gives information about the cursor
        function.
        
        PARAMETERS
        ----------
        tag_str (string): Cursor tag string.

        """
        name_str = self.tag.get_text() # current cursor text string
        match_str = re.search(r'\((\d+)\)', name_str) 
        id_str = match_str.group(0) # integer plus paren.
        try: 
            new_tag = tag_str + id_str
        # except Exception as e:
        #     print e.message
        except TypeError:
            new_tag = id_str
        self.tag.set_text(new_tag)
        
        
    def get_color(self):
        """Return the cursor line color.
        """
        cur_color = self.color
        # cur_color = self.cline.get_color()
        return cur_color


    def set_color(self, color):
        """Set main cursor color.

        Parameters
        ----------
        color (string): Cursor and text color.
        """
        self.color = color
        self.cline.set_color(color)
        self.tag.set_color(color)
        self.ax.get_figure().show()

        
    def get_xpos(self):
        """Return the cursor x axis position.
        """
        xpos = self.cline._xy[0][0]
        return xpos

        
    def _connect(self):
        """Connect callback functions to event manager.
        """
        # Connect to all the events we need
        self.cidpress = self.cline.figure.canvas.mpl_connect(
            'button_press_event', self._on_press)
        self.cidrelease = self.cline.figure.canvas.mpl_connect(
            'button_release_event', self._on_release)
        self.cidmotion = self.cline.figure.canvas.mpl_connect(
            'motion_notify_event', self._on_motion)


    def _on_press(self, event):
        if event.inaxes != self.cline.axes: return
        if self.mode == 'fixed': return # no interaction 
        # Navigation mode in 'PAN' or 'ZOOM'
        if self.ax._navigate_mode != None: return
        # 'contains' (type 'bool')
        # 'attrd' (type 'dict')
        contains, attrd = self.cline.contains(event)
        if not contains: return
        x0, y0 = self.cline._xy[0]
        self._press = x0, y0, event.xdata, event.ydata
        # Delete cursor upon right mouse button press
        # (navigation mode not in 'PAN' or 'ZOOM')
        # Do not delete when part of span
        if event.button == 3 and self.orient != 'vertspan':
            remcur(self)
        

    def _on_motion(self, event):
        if self._press is None: return
        if event.inaxes != self.cline.axes: return
        x0, y0, xpress, ypress = self._press
        self.cline.set_xdata(event.xdata) # set cursor position 
        self.tag.set_x(event.xdata)
        self.cline.figure.canvas.draw()
        # Update location if part of a span
        if self.orient == 'vertspan':
            self.spanobj.updatespan()


    def _on_release(self, event):
        #print('button_release_event')
        self._press = None
        self.cline.figure.canvas.draw()


class DragSpan(object):
    def __init__(self, ax, low_pos, high_pos, mode='interact', **kwargs):
        """Constructor.
        """
        self.ax = ax
        # Cursor & span properties
        spanprops = kwargs.get('spanprops', {})
        curprops = kwargs.get('curprops', {})
        # Span and cursors have same color
        self.color = curprops.get('color', 'r') 
        
        # Attach instance list to axes
        if hasattr(ax, 'spanlist'):
            ax.spanlist.append(self)
        else:
            ax.spanlist = [self]

        # Place two cursors
        self.span_low = DragCursor(ax, low_pos,
                                   orient='vertspan',
                                   mode='interact', **curprops)
        self.span_high = DragCursor(ax, high_pos,
                                    orient='vertspan',
                                    mode='interact', **curprops)

        # Attach span object to cursors
        self.span_low.spanobj = self
        self.span_high.spanobj = self

        # Create fill between cursors (span)
        self.vspan = self.ax.axvspan(low_pos, high_pos,
                                     **spanprops)
        plt.show()
        self._connect()


    def set_color(self, color):
        """Set main cursor color.

        PARAMETERS
        ----------
        color (string): Axspan, cursor and text color.
        """
        self.color = color
        # Set cursor color
        self.span_low.set_color(color)
        self.span_high.set_color(color)
        # Set the axspan color
        self.vspan.set_edgecolor(color)
        # Update figure
        self.ax.get_figure().show()


    def get_color(self):
        """Return the span color.
        """
        span_color = self.color
        return span_color
        
        
    def get_tag(self):
        """Get the span tag.

        Usually, the span tag is identical to one of the two cursor
        tags.
        
        RETURNS
        -------
        tag_str (string): Span tag string.
        """
        tag_str = self.span_low.get_tag()

        
    def set_tag(self, tag_str):
        """Set the span tag.
        
        The cursor ID is preserved and appended to the cursor tag
        string. The span tag string gives information about the cursor
        function.
        
        Parameters
        ----------
        tag_str (string): Span tag string.
        """
        self.span_low.set_tag(tag_str)
        self.span_high.set_tag(tag_str)
        
        
    def _connect(self):
        # Connect to all the events we need
        self.cidpress = self.vspan.figure.canvas.mpl_connect(
            'button_press_event', self._on_press)


    def _on_press(self, event):
        if event.inaxes != self.vspan.axes: return
        if self.ax._navigate_mode != None: return
        if self.span_low.mode == 'fixed': return # no interaction 
        contains, attrd = self.vspan.contains(event)
        if not contains: return
        # Delete span upon right mouse button press
        if event.button == 3:
            self.delspan(event)

            
    def updatespan(self):
        """Update span (fill) according to current cursor positions.
        """
        low_val = self.span_low.cline._x[0]
        high_val = self.span_high.cline._x[0]
        # print('x values: ', low_val, high_val)

        xy_coord = np.array([[ low_val,  0. ],
                             [ low_val,  1. ],
                             [ high_val,  1. ],
                             [ high_val,  0. ],
                             [ low_val,  0. ]])
        self.vspan.set_xy(xy_coord)

        
    def delspan(self, event):
        """Delete span and cursors and disconnect any callback.
        """
        remcur(self.span_low)
        remcur(self.span_high)
        self.vspan.remove()
        self.ax.spanlist.remove(self)
        # Disconnet callbacks
        self.vspan.figure.canvas.mpl_disconnect(self.cidpress)

        
if __name__ == "__main__":
    pass
