#!/usr/bin/env python
"""resinOS version distribution plot

Display the resinOS versions as time series, based on the fleet score data record.
"""
from datetime import datetime
import numpy
import xlrd
import semver
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

MC_VERSION = ">=2.12.0"


def get_date(datestring):
    """ Convert a 'YYYYMMDD' format into a date object

    Args:
        datestring (string): the date to convert, in 'YYMMDD' format

    Rerturn:
        datetime.date: the resulting date object
    """
    return datetime.strptime(datestring, "%Y%m%d").date()


def load_counts(workbook):
    """ Create a dictionary with the device version counts time series
    from the given spreadsheetself.

    Args:
        workbook (xlrd.book.Book): a fleetscore spreadsheet in XLS format

    Returns:
        dict: the collected time series data, with the key being the OS version,
            and the value is an (, 2) numpy array, with date | count columns
    """
    date_sheets = workbook.sheet_names()[3:]  # first 3 sheets are not needed:
    # OS version, supervisor version, mods
    dates = numpy.empty((0, 2))
    # Add a row for each date we find
    for date_sheet_name in date_sheets:
        dates = numpy.append(
            dates, numpy.array([[get_date(date_sheet_name), 0]]), axis=0
        )

    # Create a dict with a copy of that empty array for all known resinOS versions
    oslist = {}
    ossheet = workbook.sheet_by_name("OSVer")
    for row_idx in range(1, ossheet.nrows):
        version = ossheet.cell(row_idx, 0).value
        oslist[version] = dates.copy()
    # Special Sheets: will hold the sum for the 1.x and 2.x devices
    extra_versions = ["1.x", "2.x", "mc-capable", "non-mc-capable"]
    for ver in extra_versions:
        oslist[ver] = dates.copy()

    # Load all the counts into the sheets by date
    for daily in date_sheets:
        daily_sheet = workbook.sheet_by_name(daily)
        daily_date = get_date(daily)
        for row_idx in range(2, daily_sheet.nrows):
            version = daily_sheet.cell(row_idx, 0).value
            count = int(daily_sheet.cell(row_idx, 2).value)
            # Up the count for the version
            dayindex = numpy.where(oslist[version] == daily_date)[0][0]
            oslist[version][dayindex, 1] += count
            # Up the count for the major verison
            if version[0] == "2":
                special_version = "2.x"
            else:
                special_version = "1.x"
            dayindex = numpy.where(oslist[special_version] == daily_date)[0][0]
            oslist[special_version][dayindex, 1] += count
            if semver.match(version, MC_VERSION):
                mc_capability = "mc-capable"
            else:
                mc_capability = "non-mc-capable"
            dayindex = numpy.where(oslist[mc_capability] == daily_date)[0][0]
            oslist[mc_capability][dayindex, 1] += count
    return oslist


def format_plot(fig, ax, title, xlim):
    """Format a plot uniformly for the time series.

    Args:
        fig (matplotlib.figure.Figure): the main figure object to format
        ax (matplotlib.axes._subplots.AxesSubplot): the corresponding subplot
        title (str): plot title
        xlim (tuple): the x-axis limit tuple
    """
    months = mdates.MonthLocator()  # every month
    days = mdates.DayLocator()  # every day
    months_format = mdates.DateFormatter("%Y %b")
    fig.autofmt_xdate()
    ax.legend()
    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(months_format)
    ax.xaxis.set_minor_locator(days)
    ax.set_title(title)
    ax.set_ylabel("Count")
    ax.set_ylim(0)
    ax.set_xlim(xlim)
    ax.grid(True)


def plot_data(oslist, special_versions):
    """Plot the version data

    Args:
        oslist (dict): collection of time series data to plot, key is the version,
            value is a timeseries
        special_versions (list): versions to highlight, which keys in oslist to emphasize
    """
    # Plot by version
    fig1, ax1 = plt.subplots(figsize=(12, 8), dpi=150)
    # Plot by major version
    fig2, ax2 = plt.subplots(figsize=(12, 8), dpi=150)
    major_versions = ["1.x", "2.x"]
    # Plot by Multicontainer (MC) capability
    fig3, ax3 = plt.subplots(figsize=(12, 8), dpi=150)
    mc_capability = ["mc-capable", "non-mc-capable"]
    # Some markers, nothing special in how many there are, could add more
    markers = [None, "o", "^", "v", "s", "d", "D", "|"]
    count = 0
    for key in oslist:
        ax = ax1
        if key in major_versions:
            ax = ax2
        if key in mc_capability:
            ax = ax3
        counts = oslist[key]
        if key in special_versions:
            linewidth = 3
            linestyle = "-"
            ax.plot(
                counts[:, 0],
                counts[:, 1],
                linewidth=linewidth,
                linestyle=linestyle,
                label=key,
                marker=markers[count % len(markers)],
            )
            count += 1
        else:
            linewidth = 1
            linestyle = "--"
            ax.plot(
                counts[:, 0], counts[:, 1], linewidth=linewidth, linestyle=linestyle
            )

    XLIM = (counts[0, 0], counts[-1, 0])
    format_plot(
        fig1, ax1, "Device count in a rolling 28-day window by OS version", XLIM
    )
    format_plot(
        fig2, ax2, "Device count in a rolling 28-day window by major OS version", XLIM
    )
    format_plot(
        fig3,
        ax3,
        "Device count in a rolling 28-day window by multicontainer capability",
        XLIM,
    )
    plt.show()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Please provide an input file as an argument to the script.",
            file=sys.stderr,
        )
        sys.exit(1)
    FLEETSCORE_FILE = sys.argv[1]
    WORKBOOK = xlrd.open_workbook(FLEETSCORE_FILE)
    OSLIST = load_counts(WORKBOOK)
    # List of versions we want to highlight.
    SPECIAL_VERSIONS = [
        "1.x",
        "2.x",
        "2.15.1",
        "2.13.6",
        "2.12.7",
        "2.12.6",
        "2.12.5",
        "2.12.3",
        "2.9.7",
        "2.7.5",
        "2.3.0",
        "2.2.0",
        "mc-capable",
        "non-mc-capable",
    ]
    plot_data(OSLIST, SPECIAL_VERSIONS)
