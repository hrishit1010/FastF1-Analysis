import os
import matplotlib
import numpy as np
import pandas as pd
import fastf1 as ff1
from fastf1 import utils, plotting
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection

# Enable local cache for faster data access
ff1.Cache.enable_cache(r"C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\cache")

# Enable FastF1 plotting setup
plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')


def get_race_data(user_input):
    """Route the analysis type to the appropriate plotting function."""
    session = ff1.get_session(int(user_input[0]), user_input[1], user_input[2])
    session.load()

    analysis = user_input[5]
    if analysis == 'Lap Time':
        compare_lap_times(session, user_input)
    elif analysis == 'Fastest Lap':
        compare_fastest_laps(session, user_input)
    elif analysis == 'Fastest Sectors':
        visualize_fastest_sectors(session, user_input)
    elif analysis == 'Full Telemetry':
        compare_full_telemetry(session, user_input)


def compare_lap_times(session, user_input):
    """Plot lap times for both drivers over the session."""
    plt.clf()
    d1 = user_input[3].split()[0]
    d2 = user_input[4].split()[0]

    laps1 = session.laps.pick_driver(d1)
    laps2 = session.laps.pick_driver(d2)

    c1 = plotting.driver_color(user_input[3])
    c2 = plotting.driver_color(user_input[4])

    fig, ax = plt.subplots()
    ax.plot(laps1['LapNumber'], laps1['LapTime'], color=c1, label=user_input[3])
    ax.plot(laps2['LapNumber'], laps2['LapTime'], color=c2, label=user_input[4])

    ax.set_xlabel('Lap')
    ax.set_ylabel('Time')
    ax.legend()
    plt.suptitle(f"Lap Time Comparison\n{session.event.year} {session.event['EventName']} {user_input[2]}")
    plt.savefig(r'C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\plot', dpi=200)


def compare_fastest_laps(session, user_input):
    """Compare car speed by distance for each driver's fastest lap."""
    plt.clf()
    d1 = user_input[3].split()[0]
    d2 = user_input[4].split()[0]

    fastest1 = session.laps.pick_driver(d1).pick_fastest()
    fastest2 = session.laps.pick_driver(d2).pick_fastest()

    tel1 = fastest1.get_car_data().add_distance()
    tel2 = fastest2.get_car_data().add_distance()

    c1 = plotting.driver_color(user_input[3])
    c2 = plotting.driver_color(user_input[4])

    fig, ax = plt.subplots()
    ax.plot(tel1['Distance'], tel1['Speed'], color=c1, label=user_input[3])
    ax.plot(tel2['Distance'], tel2['Speed'], color=c2, label=user_input[4])

    ax.set_xlabel('Distance (m)')
    ax.set_ylabel('Speed (km/h)')
    ax.legend()
    plt.suptitle(f"Fastest Lap Comparison\n{session.event.year} {session.event['EventName']} {user_input[2]}")
    plt.savefig(r'C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\plot', dpi=700)


def visualize_fastest_sectors(session, user_input):
    """Visualize which driver is fastest in each mini-sector of a specific lap."""
    plt.clf()
    drivers = [user_input[3].split()[0], user_input[4].split()[0]]
    all_data = pd.DataFrame()

    for driver in drivers:
        for lap in session.laps.pick_driver(driver).iterlaps():
            telemetry = lap[1].get_telemetry().add_distance()
            telemetry['Driver'] = driver
            telemetry['Lap'] = lap[1]['LapNumber']
            all_data = pd.concat([all_data, telemetry])

    all_data = all_data[['Lap', 'Distance', 'Driver', 'Speed', 'X', 'Y']]
    all_data['Minisector'] = pd.cut(all_data['Distance'], 25, labels=False) + 1
    avg_speed = all_data.groupby(['Lap', 'Minisector', 'Driver'])['Speed'].mean().reset_index()
    sector_results = resolve_sector_battle(avg_speed, user_input)

    all_data = all_data.merge(sector_results, on='Minisector').sort_values(by='Distance')
    all_data['fastest_driver_int'] = np.where(
        all_data['fastest_driver'] == drivers[0], 1, 2
    )

    lap_number = int(user_input[6])
    lap_data = all_data[all_data['Lap'] == lap_number]
    points = np.array([lap_data['X'].values, lap_data['Y'].values]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    color_array = lap_data['fastest_driver_int'].astype(float).to_numpy()

    cmap = matplotlib.colors.ListedColormap([
        matplotlib.colors.to_rgb(plotting.driver_color(user_input[3])),
        matplotlib.colors.to_rgb(plotting.driver_color(user_input[4]))
    ])

    lc = LineCollection(segments, norm=plt.Normalize(1, 2), cmap=cmap)
    lc.set_array(color_array)
    lc.set_linewidth(2)

    plt.rcParams['figure.figsize'] = [6.25, 4.70]
    plt.gca().add_collection(lc)
    plt.axis('equal')
    plt.axis('off')

    plt.legend(
        [Line2D([0], [0], color=cmap.colors[0]), Line2D([0], [0], color=cmap.colors[1])],
        [user_input[3], user_input[4]],
        loc='upper right'
    )

    plt.suptitle(f"Fastest Minisectors (Lap {lap_number})\n{session.event.year} {session.event['EventName']} {user_input[2]}")
    plt.savefig(r'C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\plot', dpi=200)


def resolve_sector_battle(avg_speed, user_input):
    """Determine which driver is faster per mini-sector."""
    driver1 = user_input[3].split()[0]
    driver2 = user_input[4].split()[0]

    d1_data = avg_speed[avg_speed['Driver'] == driver1]
    d2_data = avg_speed[avg_speed['Driver'] == driver2]

    final = pd.DataFrame(columns=['Minisector', 'fastest_driver'])

    for idx in range(min(len(d1_data), len(d2_data))):
        s1 = d1_data.iloc[idx]
        s2 = d2_data.iloc[idx]
        faster_driver = s1['Driver'] if s1['Speed'] > s2['Speed'] else s2['Driver']
        final.loc[len(final)] = [s1['Minisector'], faster_driver]

    return final


def compare_full_telemetry(session, user_input):
    """Compare speed, throttle, brake, RPM, gear and delta time for both drivers."""
    plt.clf()
    d1 = user_input[3].split()[0]
    d2 = user_input[4].split()[0]

    fastest1 = session.laps.pick_driver(d1).pick_fastest()
    fastest2 = session.laps.pick_driver(d2).pick_fastest()

    tel1 = fastest1.get_car_data().add_distance()
    tel1['Brake'] = tel1['Brake'].astype(int)
    tel2 = fastest2.get_car_data().add_distance()
    tel2['Brake'] = tel2['Brake'].astype(int)

    delta, ref_tel, _ = utils.delta_time(fastest1, fastest2)

    fig, axes = plt.subplots(6, sharex=True)
    props = [tel1, tel2]
    colors = [plotting.driver_color(user_input[3]), plotting.driver_color(user_input[4])]

    for tel, col in zip(props, colors):
        axes[0].plot(ref_tel['Distance'], delta, color=col, lw=0.8)
        axes[1].plot(tel['Distance'], tel['Speed'], color=col)
        axes[2].plot(tel['Distance'], tel['Throttle'], color=col)
        axes[3].plot(tel['Distance'], tel['Brake'], color=col)
        axes[4].plot(tel['Distance'], tel['RPM'], color=col)
        axes[5].plot(tel['Distance'], tel['nGear'], color=col)

    labels = ['Delta (s)', 'Speed', 'Throttle', 'Brake', 'RPM', 'Gear']
    for ax, label in zip(axes, labels):
        ax.set_ylabel(label)

    axes[0].legend([
        Line2D([0], [0], color=colors[0]), Line2D([0], [0], color=colors[1])
    ], [user_input[3], user_input[4]], loc='lower right', prop={'size': 6})

    plt.suptitle(f"Telemetry Comparison\n{user_input[3]} vs {user_input[4]} - {session.event.year} {session.event['EventName']} {user_input[2]}")
    plt.savefig(r'C:\Users\hrish\Downloads\formula1-telemetry-tool-main\formula1-telemetry-tool-main\plot', dpi=200)
