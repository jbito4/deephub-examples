#!/usr/bin/env python3
import time
import threading
import requests as rest
import DeepHubClasses as dh
import random
import math
import datetime
import pyproj
import matplotlib.pyplot as plt
import websocket

# The URL at which the DeepHub is running. Adjust this accordingly if running the DeepHub at some other URL.
url = 'http://localhost:8081/deephub/v1'

# A constant to improve readability of the code
REVERSE = True

# An id used for identifying the zone created for this example.
zone_foreign_id = 'mathematikon.example1.zone'

# The id of the location provider of the example's truck.
provider_id_truck = 'TRUCK_GPS_HARDWARE_ID'
provider_id_truck2 = 'ACCURO_THEIA_HARDWARE_ID'

# The ids of the location providers of the example's forklift.
provider_id_forklift_gps = 'FORKLIFT_GPS_HARDWARE_ID'
provider_id_forklift_uwb = 'FORKLIFT_UWB_TAG_ID'

# The URL to access the example's trackable. This requires the UUID of the trackable found in the DeepHub and is set during setup.
trackable_url: str


#
# The main function running the example.
#
def main():
    stored_coordinates = []  # To store the result from the thread

    def thread_function():
        nonlocal stored_coordinates
        stored_coordinates = (send_location_updates_fakedata(provider_id_truck2, 'gps'))

    # Confirm that the DeepHub can be contacted.
    if not is_healthy():
        return

    # Setup the example environment.
    print('Setting up the example.')
    setup()

    # Run the example in a loop.
    print('Running the example loop.')
    while True:

        # The pallet is loaded onto the truck, which then drives off.
        attach_trackable_to_provider(provider_id_truck)
        time.sleep(1)
        truck_thread = threading.Thread(target=send_location_updates,
                                        args=[provider_id_truck, 'gps',
                                              'truckGpsCoordinates.txt'],
                                        daemon=True)

        # truck_thread2 = threading.Thread(target=send_location_updates_fakedata,
        #                                 args=[provider_id_truck2, 'gps'],
        #                                 daemon=True)
        truck_thread2 = threading.Thread(target=thread_function, daemon=True)

        # The forklift drives to the delivery area.
        fork_gps_thread = threading.Thread(target=send_location_updates,
                                           args=[provider_id_forklift_gps, 'gps',
                                                 'forkliftGpsCoordinates.txt'],
                                           daemon=True)
        fork_uwb_thread = threading.Thread(target=send_location_updates,
                                           args=[provider_id_forklift_uwb, 'uwb',
                                                 'forkliftUwbCoordinates.txt'],
                                           daemon=True)
        fork_gps_thread.start()
        fork_uwb_thread.start()
        truck_thread.start()
        truck_thread2.start()

        # Wait for both vehicles to finish their current movement.
        fork_gps_thread.join()
        fork_uwb_thread.join()
        truck_thread.join()
        truck_thread2.join()

        # ### Plot for debug ###
        # # Extract longitude and latitude values from stored_coordinates
        # longitudes, latitudes = zip(*stored_coordinates)
        #
        # # Create a scatter plot of the coordinates
        # plt.scatter(longitudes, latitudes, marker='o', color='b', label='Coordinates')
        # plt.xlabel('Longitude')
        # plt.ylabel('Latitude')
        # plt.title('Generated Coordinates')
        # plt.legend()
        # plt.grid(True)
        # plt.show()

        # The forklift loads the pallet and drives to the drop off point.
        attach_trackable_to_provider(provider_id_forklift_uwb)
        time.sleep(1)
        fork_gps_thread = threading.Thread(target=send_location_updates,
                                           args=[provider_id_forklift_gps, 'gps',
                                                 'forkliftGpsCoordinates.txt', REVERSE],
                                           daemon=True)
        fork_uwb_thread = threading.Thread(target=send_location_updates,
                                           args=[provider_id_forklift_uwb, 'uwb',
                                                 'forkliftUwbCoordinates.txt', REVERSE],
                                           daemon=True)
        # The truck drives back to the drop off point.
        truck_thread = threading.Thread(target=send_location_updates,
                                        args=[provider_id_truck, 'gps',
                                              'truckGpsCoordinates.txt', REVERSE],
                                        daemon=True)
        # truck_thread2 = threading.Thread(target=send_location_updates_fakedata,
        #                                 args=[provider_id_truck2, 'gps'],
        #                                 daemon=True)

        fork_gps_thread.start()
        fork_uwb_thread.start()
        truck_thread.start()
        # truck_thread2.start()


        expiration_time = 60
        response = get_provider_location(url, provider_id_truck2)
        tf = check_expiration(response, expiration_time)
        if tf:
            delete_provider(url, provider_id_truck2)

        # Wait for both vehicles to finish their current movement.
        fork_gps_thread.join()
        fork_uwb_thread.join()
        truck_thread.join()
        # truck_thread2.join()

        setup()

#
# Check whether a DeepHub instance is available at the given URL.
#
def is_healthy():
    try:
        return rest.get(url + "/health").status_code == 200
    except:
        print('Could not find a DeepHub instance running at', url)
        False


#
# Initialize all the example entities in the DeepHub.
#
def setup():
    global trackable_url

    # Check whether the example's entities exist already.
    if len(rest.get(url + '/zones' + '?foreign_id=' + zone_foreign_id).json()) > 0:
        print('Found an example zone. Using existing setup.')
        trackable_id_pallet = rest.get(url + '/trackables').json()[0]
        trackable_url = url + '/trackables/' + trackable_id_pallet
        return

    # Setup the example's zone.
    zone = dh.Zone()
    zone.name = 'Area'
    zone.foreign_id = zone_foreign_id
    rest.post(url + '/zones', zone.to_json())

    # Setup the example's fences.
    delivery_fence = dh.Fence(region=dh.Polygon())
    delivery_fence.name = 'Delivery'
    rest.post(url + '/fences', delivery_fence.to_json())

    print('Making a new fence')
    new_fence = dh.Fence(region=dh.Polygon1())
    new_fence.name = 'NewFence'
    rest.post(url + '/fences', new_fence.to_json())

    drop_fence = dh.Fence(region=dh.Point())
    drop_fence.name = 'Drop'
    drop_fence.radius = 2
    rest.post(url + '/fences', drop_fence.to_json())

    # Setup the example's providers for the truck and forklift.
    provider_truck_gps = dh.LocationProvider(id=provider_id_truck)
    provider_truck_gps.name = 'Truck GPS'
    provider_truck_gps.type = 'gps'
    rest.post(url + '/providers', provider_truck_gps.to_json())

    provider_truck_gps2 = dh.LocationProvider(id=provider_id_truck2)
    provider_truck_gps2.name = 'Accuro'
    provider_truck_gps2.type = 'gps'
    rest.post(url + '/providers', provider_truck_gps2.to_json())

    provider_forklift_gps = dh.LocationProvider(id=provider_id_forklift_gps)
    provider_forklift_gps.name = 'Forklift GPS'
    provider_forklift_gps.type = 'gps'
    rest.post(url + '/providers', provider_forklift_gps.to_json())

    provider_forklift_uwb = dh.LocationProvider(id=provider_id_forklift_uwb)
    provider_forklift_uwb.name = 'Forklift UWB'
    provider_forklift_uwb.type = 'uwb'
    rest.post(url + '/providers', provider_forklift_uwb.to_json())

    # Setup the example's trackable.
    trackable_pallet = dh.Trackable()
    trackable_pallet.name = 'Pallet'
    trackable_pallet.radius = 1
    response = rest.post(url + '/trackables', trackable_pallet.to_json())
    # Obtain the trackables UUID from the response.
    trackable_id_pallet = response.json()['id']
    trackable_url = url + '/trackables/' + trackable_id_pallet



#
# Send location updates for the provider with the given id from the given file.
#
def send_location_updates(provider_id: str, provider_type: str, file: str, reverse: bool = False):
    location = dh.Location(provider_id=provider_id,
                           provider_type=provider_type)
    if provider_type == 'gps':
        location.crs = 'EPSG:4326'
    else:
        location.source = zone_foreign_id

    with open(file) as input:
        if reverse:
            input = reversed(list(input))
        for coordinates in [list(map(float, line.split(sep=','))) for line in input]:
            location.position = dh.Point(coordinates=coordinates)
            rest.put(url + '/providers/locations', location.to_json_list())
            time.sleep(0.05)


def generate_coordinates():
    # Centergy -84.389556, 33.777556
    longitude = 8.676234 + random.uniform(-0.00001, 0.00001)
    latitude = 49.415941 + random.uniform(-0.00001, 0.00001)
    return [longitude, latitude]


# define a function that takes lo, la, xm, and ym as input and returns lot and lat as output
# def convert_location_in_wgs(lo, la, xm, ym):
#     # define WGS84 constants
#     a = 6378137.0  # semi-major axis in meters
#     f = 1.0 / 298.257223563  # flattening
#     b = a - f * a  # semi-minor axis in meters
#     e = math.sqrt((a ** 2 - b ** 2) / a ** 2)  # eccentricity
#
#     # convert lo and la from degrees to radians
#     lo_rad = math.radians(lo)
#     la_rad = math.radians(la)
#
#     # convert lo, la, and h (assumed to be zero) to ECEF coordinates (x, y, z)
#     N = a / math.sqrt(1 - e ** 2 * math.sin(la_rad) ** 2)  # prime vertical radius of curvature
#     x = (N + 0) * math.cos(la_rad) * math.cos(lo_rad)  # x coordinate in meters
#     y = (N + 0) * math.cos(la_rad) * math.sin(lo_rad)  # y coordinate in meters
#     z = (N * (1 - e ** 2) + 0) * math.sin(la_rad)  # z coordinate in meters
#
#     # add xm and ym to x and y to get the ECEF coordinates of the target (xt, yt, zt)
#     xt = x + xm
#     yt = y + ym
#     zt = z  # assume no change in height
#
#     # convert xt, yt, and zt to geodetic coordinates (lt_rad, ln_rad, ht)
#     p = math.sqrt(xt ** 2 + yt ** 2)  # distance from z-axis
#     theta = math.atan2(zt * a, p * b)  # auxiliary angle
#     lt_rad = math.atan2(zt + e ** 2 * b * math.sin(theta) ** 3,
#                         p - e ** 2 * a * math.cos(theta) ** 3)  # latitude in radians
#     ln_rad = math.atan2(yt, xt)  # longitude in radians
#     Nt = a / math.sqrt(1 - e ** 2 * math.sin(lt_rad) ** 2)  # prime vertical radius of curvature at target
#     ht = p / math.cos(lt_rad) - Nt  # height in meters
#
#     # convert lt_rad and ln_rad from radians to degrees
#     lot = math.degrees(ln_rad)  # longitude in degrees
#     lat = math.degrees(lt_rad)  # latitude in degrees
#
#     # return lot and lat as output
#     return [lot, lat]


def convert_location_in_wgs(lo, la, xm, ym):
    # Define WGS84 constants
    a = 6378137.0  # semi-major axis in meters
    f = 1.0 / 298.257223563  # flattening
    b = a - f * a  # semi-minor axis in meters
    e = math.sqrt((a ** 2 - b ** 2) / a ** 2)  # eccentricity

    # Convert lo and la from degrees to radians
    lo_rad = math.radians(lo)
    la_rad = math.radians(la)

    # Convert lo, la, and h (assumed to be zero) to ECEF coordinates (x, y, z)
    N = a / math.sqrt(1 - e ** 2 * math.sin(la_rad) ** 2)  # prime vertical radius of curvature
    x = (N + 0) * math.cos(la_rad) * math.cos(lo_rad)  # x coordinate in meters
    y = (N + 0) * math.cos(la_rad) * math.sin(lo_rad)  # y coordinate in meters
    z = (N * (1 - e ** 2) + 0) * math.sin(la_rad)  # z coordinate in meters

    # Convert xm and ym to ECEF coordinates (xe, ye, ze)
    xe = x + xm
    ye = y + ym
    ze = z  # assume no change in height

    # Convert xe, ye, and ze to geodetic coordinates (lt_rad, ln_rad, ht)
    p = math.sqrt(xe ** 2 + ye ** 2)  # distance from z-axis
    theta = math.atan2(ze * a, p * b)  # auxiliary angle
    lt_rad = math.atan2(ze + e ** 2 * b * math.sin(theta) ** 3,
                        p - e ** 2 * a * math.cos(theta) ** 3)  # latitude in radians
    ln_rad = math.atan2(ye, xe)  # longitude in radians
    Nt = a / math.sqrt(1 - e ** 2 * math.sin(lt_rad) ** 2)  # prime vertical radius of curvature at target
    ht = p / math.cos(lt_rad) - Nt  # height in meters

    # Convert lt_rad and ln_rad from radians to degrees
    lot = math.degrees(ln_rad)  # longitude in degrees
    lat = math.degrees(lt_rad)  # latitude in degrees

    # Return lot and lat as output
    return [lot, lat]


def send_location_updates_fakedata(provider_id: str, provider_type: str):
    location = dh.Location(provider_id=provider_id,
                           provider_type=provider_type)
    if provider_type == 'gps':
        location.crs = 'EPSG:4326'
    else:
        location.source = zone_foreign_id

    n = 250
    r = 10
    stored_coordinates = []
    for i in range(n):
        # coordinates = generate_coordinates()
        x, y = calculate_coordinates(r, n, i)
        coordinates = convert_location_in_wgs(-84.389556, 33.778000, x, y)
        stored_coordinates.append(coordinates)  # Store the coordinates
        location.position = dh.Point(coordinates=coordinates)
        rest.put(url + '/providers/locations', location.to_json_list())
        time.sleep(0.05)
        response = get_provider_location(url, provider_id)
        print_coordinate(response)

    return stored_coordinates

def delete_provider(url: str, provider_id: str):
    endpoint = '/providers/' + provider_id
    # print('url to delete', url + endpoint)
    print('delete', provider_id)
    response = rest.delete(url + endpoint)


def get_provider_location(url: str, provider_id: str):
    endpoint = '/providers/' + provider_id + '/location/'
    print('get the location of:', provider_id)
    response = rest.get(url + endpoint)
    return response


# define a function that takes response as input and prints the coordinates
def print_coordinate(response):
    # assume response is a variable that stores the response object
    data = response.json()  # parse the response object to a Python object
    position = data["position"]  # get the position dictionary from the data
    coordinates = position["coordinates"]  # get the coordinates list from the position
    latitude = coordinates[0]  # get the first element of the list
    longitude = coordinates[1]  # get the second element of the list
    print("Longitude, Latitude:", longitude, latitude)

#
# Update the pallet trackable such that it is attached to the provider with the given id.
#
def attach_trackable_to_provider(provider_id: str):
    trackable_pallet = dh.Trackable(rest.get(trackable_url).json())
    trackable_pallet.location_providers = [provider_id]
    rest.put(trackable_url, trackable_pallet.to_json())


# define a function that takes r, cx, cy, and n as input and returns x and y as output
def calculate_coordinates(r, n, i):
    # calculate the angle increment for each step
    angle_increment = 2 * math.pi / n
    # calculate the angle for the current step
    angle = i * angle_increment
    # subtract the angle from 2 * math.pi to rotate clockwise
    angle = 2 * math.pi - angle
    # calculate the x and y coordinates using the parametric equations
    x = r * math.cos(angle)
    y = r * math.sin(angle)
    # print("x, y:", x, y)
    return x, y

def check_expiration(response, expiration_time):
    data = response.json()  # parse the response object to a Python object
    # get the timestamp_generated from the response
    timestamp = data["timestamp_generated"]
    # parse the timestamp string to a datetime object
    timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    # get the current time in UTC
    current_time = datetime.datetime.utcnow()

    print("timestamp, current time:",timestamp, current_time)
    # calculate the difference between current time and timestamp
    difference = current_time - timestamp
    # convert expiration_time from seconds to a timedelta object
    expiration_time = datetime.timedelta(seconds=expiration_time)
    # compare the difference with expiration_time
    if difference > expiration_time:
        # return True if difference is greater than expiration_time
        return True
    else:
        # return False otherwise
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped')
