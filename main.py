"""Main Simulation Controller"""
import math
import traci
import logging
import security.security_manager as security_manager
import security.settings as settings
from datetime import datetime, timezone
from utilities import v2v_functions, v2p_functions
from security.security_manager import VehicleHardwareSecurityModule, InfrastructureHardwareSecurityModule, CertifyingAuthority

# Logging Configuration
logging.basicConfig(
    # File Related Info
    filename='simulation.log',
    encoding="utf-8",
    filemode="a",

    # Other Configuration
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s \t| %(message)s"
)
logger = logging.getLogger(__name__) # we will be using this logger

def vehicle_in_front(veh_id, vehicles_data, max_angle=30, max_distance=50):
    """Return ID of the vehicle in front, if any."""
    ego = vehicles_data[veh_id]
    ego_x, ego_y = ego['x_position'], ego['y_position']
    ego_heading = ego['heading']

    min_dist = float('inf')
    front_vehicle = None

    for other_id, other in vehicles_data.items():
        if other_id == veh_id:
            continue
        
        dx = other['x_position'] - ego_x
        dy = other['y_position'] - ego_y
        distance = math.sqrt(dx**2 + dy**2)
        if distance > max_distance:
            continue

        # Angle between ego heading and vector to other vehicle
        angle_to_other = (math.degrees(math.atan2(dy, dx)) + 360) % 360
        rel_angle = (angle_to_other - ego_heading + 360) % 360
        if rel_angle > 180:  # normalize to -180..180
            rel_angle -= 360

        if abs(rel_angle) <= max_angle:  # within forward cone
            if distance < min_dist:
                min_dist = distance
                front_vehicle = other_id

    return front_vehicle, min_dist if front_vehicle else None

def predict_collision(veh_id, other_id, vehicles_data, other_entity_data, type, safe_ttc=3):
    ego = vehicles_data[veh_id]
    other = other_entity_data[other_id]

    dx = other['x_position'] - ego['x_position']
    dy = other['y_position'] - ego['y_position']
    distance = None

    if type == "VEH":
        distance = math.sqrt(dx**2 + dy**2) - ego['length']/2 - other['length']/2
    else:
        distance = math.sqrt(dx**2 + dy**2) - ego['length']/2 - other['width']/2

    rel_speed = ego['speed'] - other['speed']  # positive means ego is faster
    if rel_speed <= 0:
        return False, None  # not closing in

    ttc = distance / rel_speed
    if 0 < ttc <= safe_ttc:
        return True, ttc  # collision predicted
    return False, ttc

class SimulationManager:
    """Manages SUMO simulation and V2X communication"""
    # ---------------------- #
    # Initializing Functions #
    # ---------------------- #

    def __init__(self):
        # CA and entity objects
        self.ca = CertifyingAuthority()
        self.simulation_entities = {
            'vehicles': {},
            'pedestrians': set(),
            'infrastructures': {}
        }

    def initialize_simulation(self):
        """Setup simulation and security components"""
        
        # start SUMO first
        try:
            traci.start(["sumo-gui", "-c", "configuration/myconfig.sumocfg"])
            logger.info("✅ Simulation Started Successfully!")
        except traci.exceptions.FatalTraCIError as error:
            logger.error(f"❌ Failed to start simulation! Error Information: {str(error)}")
            raise

    def collect_simulation_data(self):
        """Gather data from SUMO simulation"""

        # simulation related data for all the entities
        data = {
            'vehicles': {},
            'pedestrians': {},
            'infrastructures': {}
        }

        # vehicle data
        for veh_id in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(veh_id)
            data['vehicles'][veh_id] = {
                'x_position': x,
                'y_position': y,
                'speed': traci.vehicle.getSpeed(veh_id),
                'heading': traci.vehicle.getAngle(veh_id),
                'length': traci.vehicle.getLength(veh_id),
                'width': traci.vehicle.getWidth(veh_id),
            }
            # initialize vehicle security if not exists
            if veh_id not in self.simulation_entities['vehicles']:
                self.simulation_entities['vehicles'][veh_id] = VehicleHardwareSecurityModule(veh_id, self.ca)
                self.simulation_entities['vehicles'][veh_id].generate_vehicle_cert()
                self._log_information("INFO", f"ℹ️ Registered vehicle: {veh_id} and issued {settings.NO_OF_VEH_CERTS} certificates.")
        
        # pedestrian data
        for ped_id in traci.person.getIDList():
            if ped_id not in self.simulation_entities['pedestrians']:
                self.simulation_entities['pedestrians'].add(ped_id)
                self._log_information("INFO", f"ℹ️ Pedestrian {ped_id} spawned.")
            
            x, y = traci.person.getPosition(ped_id)
            data['pedestrians'][ped_id] = {
                'x_position': x,
                'y_position': y,
                'speed': traci.person.getSpeed(ped_id),
                'width': traci.person.getWidth(ped_id)
            }
        
        # infrastructure data
        for infra_id in traci.trafficlight.getIDList():
            data['infrastructures'][infra_id] = {
                'state': traci.trafficlight.getRedYellowGreenState(infra_id)
            }
            # initialize vehicle security if not exists
            if infra_id not in self.simulation_entities['infrastructures']:
                self.simulation_entities['infrastructures'][infra_id] = InfrastructureHardwareSecurityModule(infra_id, self.ca)
                self.simulation_entities['infrastructures'][infra_id].generate_infra_cert()
                self._log_information("INFO", f"ℹ️ Registered infrastructure: {infra_id} and issued certificate.")
            
        return data
    
    # --------------------------- #
    # V2X Communication Functions #
    # --------------------------- #

    def handle_v2v_communication(self, vehicles_data):
        """Process Vehicle-to-Vehicle communication"""

        vehicle_ids = list(vehicles_data.keys())
        for i in range(len(vehicle_ids)):       # loop for vehicle 1
            for j in range(len(vehicle_ids)):   # loop for vehicle 2
                if i == j:
                    continue

                veh1_id, veh2_id = vehicle_ids[i], vehicle_ids[j]
                distance = v2v_functions.find_distance(
                    vehicles_data[veh1_id], 
                    vehicles_data[veh2_id]
                )
                
                if distance <= settings.BSM_DISTANCE:
                    # create and sign BSMs if the vehicles are <= settings.BSM_DISTANCE
                    # checking which vehicle is in the front
                    front_vehicle, _ = vehicle_in_front(veh1_id, vehicles_data)

                    if front_vehicle:
                        # checking if the vehicles will collide or not (and time to collision too!)
                        will_collide, ttc = predict_collision(veh1_id, front_vehicle, vehicles_data, vehicles_data, "VEH")
                        
                        if will_collide:
                            # BSM, vehicle 1 message preparation
                            message1 = self.simulation_entities['vehicles'][veh1_id].prepare_message({
                                'message_type': 'V2V/BSM',                                                      # communication type / message type
                                'vehicle_id': veh1_id,                                                          # vehicle id in simulation
                                'message_count': self.simulation_entities['vehicles'][veh1_id].message_count,   # current message count with the corresponding certificate id
                                'timestamp': datetime.now(timezone.utc).isoformat(),                            # current time
                                'latitude': vehicles_data[veh1_id]['x_position'],        # vehicle X Position
                                'longitude': vehicles_data[veh1_id]['y_position'],       # vehicle Y Position
                                'elevation': None,                                       # no hardware, field of no use
                                'accuracy': None,                                        # no hardware, field of no use
                                'transmission': None,                                    # no hardware, field of no use
                                'speed': vehicles_data[veh1_id]['speed'],                # vehicle speed
                                'heading': vehicles_data[veh1_id]['heading'],            # vehicle speed
                                'angle': None,                                           # no hardware, field of no use
                                'accelSet': None,                                        # no hardware, field of no use
                                'brakes': None,                                                                 # no hardware, field of no use
                                'size': (vehicles_data[veh1_id]['length'], vehicles_data[veh1_id]['width'])     # size of vehicle
                            })
                            # BSM, vehicle 2 message preparation
                            message2 = self.simulation_entities['vehicles'][veh2_id].prepare_message({
                                'message_type': 'V2V/BSM',
                                'vehicle_id': veh2_id,
                                'message_count': self.simulation_entities['vehicles'][veh2_id].message_count,
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'latitude': vehicles_data[veh2_id]['x_position'],
                                'longitude': vehicles_data[veh2_id]['y_position'],
                                'elevation': None,
                                'accuracy': None,
                                'transmission': None,
                                'speed': vehicles_data[veh2_id]['speed'],
                                'heading': vehicles_data[veh2_id]['heading'],
                                'angle': None,
                                'accelSet': None,
                                'brakes': None,
                                'size': (vehicles_data[veh2_id]['length'], vehicles_data[veh2_id]['width'])
                            })

                            # verify received messages
                            verification1 = security_manager.message_verifier(message1, self.ca) # for message sent by vehicle 1
                            verification2 = security_manager.message_verifier(message2, self.ca) # for message sent by vehicle 2
                            self._log_information("WARNING", f"⚠️🚗 Potential collision: Vehicle {veh1_id} ⇆ Vehicle {front_vehicle} in approximately {ttc:.2f}s\n" +
                                "\t\t\t\t\t\t\t\t\t\t\t\t\t" + f"Vehicle {veh1_id} → Vehicle {veh2_id} | Status: {verification1}\n" +
                                "\t\t\t\t\t\t\t\t\t\t\t\t\t" + f"Vehicle {veh1_id} ← Vehicle {veh2_id} | Status: {verification2}"
                            )

    def handle_v2p_communication(self, vehicles_data, pedestrians_data):
        """Process Vehicle-to-Pedestrian communication"""

        for veh_id, vehicle in vehicles_data.items():           # loop for vehicle
            for ped_id, pedestrian in pedestrians_data.items(): # loop for pedestrian
                distance = v2p_functions.find_v2p_distance(vehicle, pedestrian)
                
                if distance <= settings.PSM_DISTANCE:
                    # create and sign PSMs if the vehicle and pedestrian are <= settings.PSM_DISTANCE

                    # checking if the vehicle and pedestrian will collide or not (and time to collision too!)
                    will_collide, ttc = predict_collision(veh_id, ped_id, vehicles_data, pedestrians_data, "PED")
                    if will_collide:
                        # PSM message preparation
                        message = self.simulation_entities['vehicles'][veh_id].prepare_message({
                            'message_type': 'V2P/PSM',                                                      # communication type / message type
                            'vehicle_id': veh_id,                                                           # vehicle id in simulation
                            'message_count': self.simulation_entities['vehicles'][veh_id].message_count,    # current message count with the corresponding certificate id
                            'timestamp': datetime.now(timezone.utc).isoformat(),                                        # current time
                            'position': (vehicles_data[veh_id]['x_position'], vehicles_data[veh_id]['y_position']),     # vehicle position [x, y]
                            'accuracy': None,                                                                           # no hardware, field is of no use
                            'speed': vehicles_data[veh_id]['speed'],        # speed of vehicle
                            'heading': vehicles_data[veh_id]['heading']     # heading of vehicle
                        })

                        # verify received message
                        verification = security_manager.message_verifier(message, self.ca)
                        self._log_information("WARNING", f"⚠️🚶 Potential collision: Vehicle {veh_id} → Pedestrian {ped_id} in approximately {ttc:.2f}s | Status: {verification}")
                    
    def handle_v2i_communication(self, vehicles_data, traffic_lights_data):    
        for veh_id, vehicle in vehicles_data.items():   # loop for vehicle
            vehicle_pos = (vehicle['x_position'], vehicle['y_position'])
            closest_infra = None            # initial value of closest infrastructure
            min_distance = float('inf')     # initial value (temporary variable)
            
            for tl_id in traffic_lights_data:   # loop for infrastructure
                distance = self._calculate_distance(vehicle_pos, traci.junction.getPosition(tl_id))
                
                # finding out nearest infrastructure
                if distance < settings.MAX_V2I_RANGE and distance < min_distance:
                    min_distance = distance
                    closest_infra = tl_id
                    
            if closest_infra:
                # SPAT message preparation
                message = self.simulation_entities['infrastructures'][closest_infra].prepare_message({
                    'message_type': 'V2I/SPAT',                                                                 # communication type / message type
                    'infrastructure_id': closest_infra,                                                         # infrastructure id in simulation
                    'message_count': self.simulation_entities['infrastructures'][closest_infra].message_count,  # current message count with the corresponding certificate id
                    'timestamp': datetime.now(timezone.utc).isoformat(),                                        # current time
                    'state': traffic_lights_data[closest_infra]['state']                                        # current traffic light state
                })
                # verify received messages
                verification = security_manager.message_verifier(message, self.ca)
                self._log_information("DEBUG", f"💬🚦 Infrastructure {closest_infra} → Vehicle {veh_id} | Status: {verification}")

    # ---------------- #
    # Action Functions #
    # ---------------- #

    def action_v2v():
        """Used to perform slowing actions on vehicle in case of collision"""
        pass
    def action_v2p():
        """Used to perform slowing actions on vehicle in case of collision"""
        pass
    def action_v2i():
        """Used to perform slowing actions on vehicle in case of collision"""
        pass

    # ---------------- #
    # Helper Functions #
    # ---------------- #

    def _calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two points"""

        return math.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)
    
    def _calculate_light_change(self, tl_id):
        """Calculate time until next traffic light state change"""

        try:
            current_time = traci.simulation.getTime()
            next_switch = traci.trafficlight.getNextSwitch(tl_id)
            return max(0, next_switch - current_time)
        except traci.exceptions.TraCIException as e:
            self._log_information("ERROR", f"❌ Error calculating light change for {tl_id}: {str(e)}")

    def _log_information(self, type, message):
        """
        This function helps to log message.
        Input: type of message and message itself
        """

        message = f"Step - {traci.simulation.getTime()} | " + message

        if type == "DEBUG":
            logger.debug(message)
        elif type == "INFO":
            logger.info(message)
        elif type == "WARNING":
            logger.warning(message)
        elif type == "ERROR":
            logger.error(message)
        else:
            logger.critical(message)

    # ----------------- #
    # Simulation Runner #
    # ----------------- #

    def run_simulation(self):
        """Main simulation loop"""

        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()                      # increment the step
                sim_data = self.collect_simulation_data()   # gather simulation data (iteration-wise)
                
                # handling all types of communications
                self.handle_v2v_communication(sim_data['vehicles'])
                self.handle_v2p_communication(sim_data['vehicles'], sim_data['pedestrians'])
                self.handle_v2i_communication(sim_data['vehicles'], sim_data['infrastructures'])
                
                # log after every 10 simulation steps are completed
                if traci.simulation.getTime() % 10 == 0:
                    logger.info(f"ℹ️ Simulation step {traci.simulation.getTime()} completed")
                    
        finally:
            traci.close()
            logger.info("✅ Simulation terminated gracefully")

# ----------- #
# Driver Code #
# ----------- #

if __name__ == "__main__":
    """Driver Code"""

    sim_mgr = SimulationManager()
    try:
        sim_mgr.initialize_simulation() # setup
        sim_mgr.run_simulation()        # run
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        raise