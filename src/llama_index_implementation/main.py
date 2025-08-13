from dotenv import load_dotenv

from agents.noaa_currents_agent import tides_and_currents


load_dotenv()


def main():
    location = "Port Orchard Marina, Port Orchard, Washington"
    start_date = "04/10/2025"
    noaa_agent_response = tides_and_currents(location, start_date)
    print(noaa_agent_response)



if __name__ == "__main__":
    main()