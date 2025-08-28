# 🚗 V2X Communication Simulator 📡
A sophisticated Vehicle-to-Everything (V2X) communication simulator demonstrating secure V2V (Vehicle-to-Vehicle), V2P (Vehicle-to-Pedestrian), and V2I (Vehicle-to-Infrastructure) interactions with a comprehensive security framework.

## ✨ Key Features
- 📊 **Simulation Capabilities**
	- 📝 *Simulation*: Simulation of vehicles, pedestrians and infrastructure (in our case, traffic lights) within the generated network.
	- 💥 *Collision Prediction*: Real-time collision prediction between simulation entities with Time-To-Collision (TTC) and distance calculations.
	- 📜 *Logging*: Comprehensive logging system with detailed security events. Total of five in-built logging levels can be used.
	- 💬 *Message Communication*: Communication of messages like Basic Safety Messages (BSM), Personal Safety Messages (PSM) and Signal Phase and Timing (SPAT).

- 🔐 **Security Implementation**
    - 🗄️ *Certifying Authority (CA)*: Public key infrastructure that can issue certificates and revoke these certificates. Uses it's own pair of keys.
    - 📟 *Hardware Security Modules (HSMs)*: HSM can be found in vehicles or infrastructure and it is used to generate key pairs, request for certificates, rotate certificates (only for vehicles), prepare messages and verify messages. Message count update is also a side process of prepare message functionality.

## 💻 Technical Information
Following are the algorithms, techniques, mathematical functions, standards, etc. used in this project:

| Used For             | Used What   |
| :----:               | :----:      |
| Hashing              | SHA256      |
| Key Curve            | SECP256R1   |
| Signature Signing    | ECDSA       |
| Protocol Used        | IEEE 1609.2 |
| Certificate Format   | X.509       |
| Message Format       | SAE J2735   |
| Payload Format       | ASN.1       |
| Key Generation       | ECC         |
| Key Encoding         | PEM         |
| Private Key Format   | PKCS8       |
| Message Encoding     | UTF-8       |
| Signature Encoding   | BASE64      |

## 📁 Repository Structure
Following is the reposioty structure and the layout of all the files that are being used in this project.
```bash
v2x-communication-simulator/
    ├── 🖥️ main.py                           # Main Simulation Controller (Main Application)
    ├── 📖 README.md                         # README file
    ├── 📋 requirements.txt                  # Requirements for the project
    ├── 📜 LICENSE                           # License
    ├── ❗ .gitignore                        # Helps to remove unnecessary files
    ├── 🛠️ utilities/
    │   ├── 📟 generate_simulation.py        # Generate simulation configuration files
    │   ├── 📟 generate_and_save_keys.py     # Generate and Save CA Keys
    │   ├── 🔧 v2p_functions.py              # V2P Geometry calculations
    │   └── 🔧 v2v_functions.py              # V2V Geometry calculations
    └── 🔒 security/
        ├── ⚙️ settings.py                   # Security configuration settings
        └── 🔐 security_manager.py           # Security Controller
```

## 🚀 Installations & Setup
1. The latest version of the [Python](https://www.python.org/) should be installed. The version during the development of this project was **Python 3.13**. No issues should be there but if you do face some issues/bugs, then contact the author. You will also require [Git](https://git-scm.com/) if you want to clone the repository.

2. Now either download and put all the files of this GitHub repositiory to this `v2x-communication-simulator` folder or clone this repositiory using the command below.
	```bash
	git clone https://github.com/vaibhavgarg9/v2x-communication-simulator.git
	cd v2x-communication-simulator
	```

3. Create and activate a Python virtual environment in the `v2x-communication-simulator` directory.
	```bash
	# Windows
	python -m venv v2x_env
	v2x_env\Scripts\activate

	# Linux/macOS
	python -m venv v2x_env
	source v2x_env/bin/activate
	```

4. Ensure that the [Simulation of Urban MObility (SUMO)](https://sumo.dlr.de/docs/index.html) is properly installed. Install this one: Installer with all extras (contains GPL code) from the SUMO website. Make sure that you click on checkbox `Set SUMO_HOME and adapt PATH and PYTHONPATH.` during installation.

5. Install Python dependencies using the following command.
	```bash
	pip install -r requirements.txt
    pip install -r "$env:SUMO_HOME\tools\requirements.txt" # on Windows (PowerShell/CMD)
	pip install -r "$SUMO_HOME/tools/requirements.txt"     # on Linux/macOS
	```

6. Run the following commands to generate the necessary files.
	```bash
	python "utilities/generate_simulation.py"
	python "utilities/generate_and_save_keys.py"
	```

When you are done using the simulation, you can deactivate the virtual environment (that was created in step 1) using the following command.
```bash
deactivate
```

## 🎮 Running Simulation
1. Run the simulation:
	```bash
	python main.py
	```
	**Note**: *The virtual environment should be active!*
2. Logs are written to `v2x_project/simulation.log`. 📜
3. That's it! You are good to go. ✅

## ⚠️ Important Implementation Notes
- Security Considerations:<br>
    🔄 Certificate rotation occurs every 10 messages (configurable).<br>
    📜 Each vehicle receives 100 pre-generated certificates.<br>
    ⏰ All timestamps are timezone-aware (UTC).<br>
    🚫 Certificate revocation is implemented via CRL.<br>
	⏱️ Issued Certificates will only be valid for 10 minutes.

- Simulation Characteristics:<br>
    ⏱️ Runs for 1000 simulation steps by default.<br>
    🚗 Supports multiple vehicle types with realistic dimensions.<br>
    🚶 Includes pedestrian movement and interactions.<br>
    🚦 Implements traffic light infrastructure with state tracking.<br>
	📏 The distance to trigger BSM is 15 and PSM is 5.

- Limitations:<br>
    🧪 Designed as a demonstration system, not production-ready.<br>
    💾 Uses in-memory storage for certificates (not persistent).<br>
    📡 Simplified propagation model (distance-based only).<br>
    🔧 Some parameters are hardcoded for simplicity.

## 🔮 Suggested Improvements & Future Enhancements
- Planned Improvements:<br>
    🗄️ Persistent storage for data.<br>
    🌐 OCSP (Online Certificate Status Protocol) implementation.<br>
    📍 Realistic GPS simulation with noise modeling.<br>
    ⚠️ Threat injection and attack simulation capabilities.<br>
    🛣️ Support for more SAE J2735 message types.<br>
    📊 Enhanced visualization and analytics.

- Potential Extensions:<br>
    🌉 Multi-intersection network support.<br>
    ☁️ Cloud-based CA and certificate distribution.<br>
    🔄 Vehicle-to-Network (V2N) communication.<br>
    🤖 Autonomous vehicle decision-making algorithms.

## 📜 License
This project is licensed under the MIT License. I have included [`LICENSE`](https://github.com/vaibhavgarg9/v2x-communication-simulator/blob/main/LICENSE) file.

## 📞 Contact & Support
For questions, support, or contributions:
- 🌐 Portfolio: https://vaibhavgarg9.github.io/portfolio-website
- 💼 LinkedIn: https://www.linkedin.com/in/vaibhav-garg-cse
- 🎮 Discord: `vaibhav_garg`