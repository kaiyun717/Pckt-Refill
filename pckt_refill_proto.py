"""
Pckt Refill (Pocket Refill)
(ME 100 - Spring 2021 :: Final Project)
"""

from mqttclient import MQTTClient
import network
import sys
import time

from hcsr04 import HCSR04

from machine import Pin


class Connection:

    def __init__(self):
        # MQTT connection information
        self.adafruit_io_url = 'io.adafruit.com'
        self.adafruit_username = 'kaileo'
        self.adafruit_aio_key = 'aio_CHOe50GxVH1hRAGMCF4XbXjHK6KE'

        # Adafruit feed
        self.feed_name = 'kaileo/feeds/pckt-refill'

        # WiFi connection information
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        self.ip = wlan.ifconfig()[0]

    def wifi_connection(self):
        """Make the WiFi connection."""
        if self.ip == '0.0.0.0':
            print("No WiFi connection. "
                  "\nPlease make sure connection is set correctly.")
            sys.exit()
        else:
            print("Connected to WiFi at IP", self.ip)

    def adafruit_connection(self):
        """Make the AdaFruit connection."""
        print("Connecting to Adafruit...")
        self.mqtt = MQTTClient(self.adafruit_io_url,
                               port='1883',
                               user=self.adafruit_username,
                               password=self.adafruit_aio_key)
        time.sleep(0.5)
        print("AdaFruit connection made at:", self.adafruit_username)

    def initial_amount_callback(self, topic, amount):
        """
        Sets initial amount for the dispenser from AdaFruit dashboard.
        :param topic: name of the topic
        :param amount: initial amount set with the toggle block
        :return: initial amount set by the user
        """
        return amount

    def on_off_callback(self, topic, msg):
        """
        ### NOT sure whether to use this ###
        Whether to turn the device on or off.
        :param topic: name of the topic
        :param msg: On or Off from AdaFruit
        :return: True or False
        """
        if msg == b"ON":
            print(msg)
            return True
        else:
            print("OFF")
            return False

    def return_ip(self):
        return self.ip

    def return_mqtt(self):
        return self.mqtt


class Dispenser:

    def __init__(self, initial_amount=1000, refill_standard=10):
        """
        Keeps track of how much hand sanitizer is left and related calculations.
        :param initial_amount: initial amount of filled hand sanitizer. (ounces)
        :param refill_standard: refill standard chosen by the user. (ounces)
        """
        self.initial_amount = initial_amount    # ounces
        self.refill_standard = refill_standard  # ounces
        self.amount_left = initial_amount        # ounces

        # Number of usages so far.
        self.number_used = 0        # count
        # Amount used per usage.
        self.per_usage = 10         # ounces
        # Distance standard for counting a usage.
        self.usage_standard = 10     # cm

    def used(self):
        """
        Count a usage.
        """
        self.number_used += 1

    def return_amount_left(self):
        """
        Calculate how much sanitizer is left and return the value.
        :return: amount_left
        """
        self.amount_left = self.initial_amount - self.number_used * self.per_usage

        return self.amount_left

    def return_initial_amount(self):
        """
        Make a way for the use to check the initial amount and return the value.
        :return: initial_amount
        """
        return self.initial_amount

    def return_refill_standard(self):
        """
        Make a way for the user to set the refill_standard and return the value.
        :return: refill_standard
        """
        return self.refill_standard

    def return_usage_standard(self):
        """
        Return the distance standard for counting the usage.
        :return: distance_usage
        """
        return self.usage_standard


class SonarSensor:

    def __init__(self):
        """
        Initiate HCSR04 SonarSensor.
        """
        self.sensor = HCSR04(trigger_pin=22, echo_pin=23, echo_timeout_us=1000000)

    def measure_distance(self):
        """
        This returns True when the sensor senses a usage.
        :return: distance
        """

        return self.sensor.distance_cm()


if __name__ == "__main__":

    # Make the internet connections: WiFi, AdaFruit, MQTT, etc.
    connection = Connection()
    connection.wifi_connection()
    connection.adafruit_connection()

    mqtt = connection.return_mqtt()
    mqtt.set_callback(connection.initial_amount_callback)
    mqtt.publish(connection.feed_name, "Pckt Refill connection made!")
    print("Connection made with Pckt-Refill interface.")
    mqtt.subscribe(connection.feed_name)

    # while True:
    #     # msg = mqtt.check_msg()
    #     # if msg is None:
    #     #     continue
    #     # else:
    #     #     ada_initial_amount = int(msg)
    #
    #     # try:
    #     #     ada_initial_amount = int(mqtt.check_msg())
    #     # except TypeError:
    #     #     continue
    #
    #     print("Initial amount set from adafruit:", mqtt.check_msg())
    #     break

    # Initialize all the LED lights.
    led_yellow = Pin(4, mode=Pin.OUT)
    led_green = Pin(27, mode=Pin.OUT)
    led_red = Pin(21, mode=Pin.OUT)

    # Initialize the Dispenser class.
    dispenser = Dispenser(initial_amount=100)
    initial_amount = dispenser.return_initial_amount()
    refill_standard = dispenser.return_refill_standard()
    usage_standard = dispenser.return_usage_standard()

    # Turn the green LED on to signal that the dispenser is full.
    led_green(1)

    # Print all the initial values for the Dispenser.
    print("Initial Amount: ", initial_amount, "Oz")
    print("Refill Standard: ", refill_standard, "Oz")
    print("Usage Standard: ", usage_standard, "cm")

    time.sleep(5)

    # Initialize the SonarSenor.
    sonar_sensor = SonarSensor()

    while True:
        distance = sonar_sensor.measure_distance()

        if distance < usage_standard:
            led_green(0)
            led_yellow(1)
            time.sleep(1)
            led_yellow(0)
            led_green(1)

            dispenser.used()

        amount_left = dispenser.return_amount_left()

        if amount_left <= refill_standard:
            led_green(0)
            led_red(1)
            print("NEED REFILL!!!")
            time.sleep(10)

            # No need to turn it off in real usage.
            # Turn off when it's refilled.
            led_red(0)
            mqtt.publish(connection.feed_name, "Dispenser empty. Need REFILL!")
            break

        print("Amount Left:", amount_left)
        time.sleep(0.5)