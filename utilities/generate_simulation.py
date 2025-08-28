import subprocess
import sys
import time
from pathlib import Path

# Get the project root directory
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.absolute()
CONFIG_DIR = PROJECT_ROOT / "configuration"

def run_command(command, description, check_returncode=True, cwd=None):
    """Run a system command and handle errors"""
    print(f"🚀 {description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
    
    if check_returncode and result.returncode != 0:
        print(f"❌ Error: {description}")
        print(f"🔧 Command: {command}")
        if result.stderr:
            print(f"📛 Error output: {result.stderr}")
        sys.exit(1)
    
    return result

def check_tool(tool_name, error_message):
    """Check if a tool is available in PATH"""
    result = subprocess.run(f"where {tool_name}", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ {error_message}")
        sys.exit(1)

def print_step(step_number, description):
    """Print a formatted step header"""
    print(f"\n📋 STEP {step_number}: {description}")

def ensure_config_dir():
    """Ensure the configuration directory exists"""
    if not CONFIG_DIR.exists():
        print(f"📁 Creating configuration directory: {CONFIG_DIR}")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def main():
    print("🎯 Starting Simulation Configuration Generation")
    print(f"📂 Output will be saved to: {CONFIG_DIR}")
    print("⏳ Please wait while we check requirements and generate files...\n")
    
    # Ensure configuration directory exists
    config_dir = ensure_config_dir()
    time.sleep(1)

    # Check for required tools
    print("🔍 Checking for required tools...")
    check_tool("python", "Python not found in PATH. Please ensure Python is installed.")
    check_tool("netgenerate", "netgenerate not found. Please ensure SUMO is properly installed.")
    check_tool("duarouter", "duarouter not found. Please ensure SUMO is properly installed.")
    
    print("✅ All required tools found successfully!")
    time.sleep(1)

    # Step 1: Generate network
    print_step(1, "Generating network [mynet.net.xml]")
    run_command(
        "netgenerate --grid --grid.number 2 --grid.attach-length 100 --output-file mynet.net.xml --turn-lanes 1 --tls.guess true --sidewalks.guess true --crossings.guess true",
        "Generating network",
        cwd=config_dir
    )
    print("✅ Network generated successfully")

    # Step 2: Find randomTrips.py
    print_step(2, "Finding randomTrips.py")
    result = subprocess.run("where randomTrips.py", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ randomTrips.py not found in PATH. Please ensure SUMO tools directory is in your PATH.")
        sys.exit(1)
    
    random_trips_path = result.stdout.strip().split('\n')[0]
    print(f"✅ Found randomTrips.py at: {random_trips_path}")

    # Step 3: Generate vehicle trips
    print_step(3, "Generating vehicle trips [vehicles.trips.raw.xml]")
    run_command(
        f'python "{random_trips_path}" -n mynet.net.xml -b 0 -e 1000 -p 5.0 --vclass passenger --validate -o vehicles.trips.raw.xml',
        "Generating vehicle trips",
        cwd=config_dir
    )
    print("✅ Vehicle trips generated successfully")

    # Step 4: Validate vehicle trips
    print_step(4, "Validating vehicle trips [vehicles.trips.xml]")
    run_command(
        "duarouter --net-file mynet.net.xml --route-files vehicles.trips.raw.xml --output-file vehicles.trips.xml --write-trips true",
        "Validating vehicle trips",
        cwd=config_dir
    )
    print("✅ Vehicle trips validated successfully")

    # Step 5: Generate vehicle routes
    print_step(5, "Generating vehicle routes [vehicles.rou.xml]")
    run_command(
        "duarouter --net-file mynet.net.xml --route-files vehicles.trips.xml --output-file vehicles.rou.xml --alternatives-output vehicles.rou.alt.xml --ignore-errors",
        "Generating vehicle routes",
        cwd=config_dir
    )
    print("✅ Vehicle routes generated successfully")

    # Step 6: Create vehicle types file
    print_step(6, "Creating vehicle types file [vehicle_types.xml]")
    vehicle_types_content = '''<?xml version="1.0" encoding="UTF-8"?>
<additional>
    <vType id="passenger" vClass="passenger" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="70" color="1,1,0"/>
</additional>'''
    
    with open(config_dir / "vehicle_types.xml", "w") as f:
        f.write(vehicle_types_content)
    
    print("✅ Vehicle type file created successfully")

    # Step 7: Generate pedestrian trips
    print_step(7, "Generating pedestrian trips [pedestrians.trips.raw.xml]")
    run_command(
        f'python "{random_trips_path}" -n mynet.net.xml -b 0 -e 1000 -p 10.0 --validate --pedestrians -o pedestrians.trips.raw.xml',
        "Generating pedestrian trips",
        cwd=config_dir
    )
    print("✅ Pedestrian trips generated successfully")

    # Step 8: Validate pedestrian trips
    print_step(8, "Validating pedestrian trips [pedestrians.trips.xml]")
    run_command(
        "duarouter --net-file mynet.net.xml --route-files pedestrians.trips.raw.xml --output-file pedestrians.trips.xml --write-trips true",
        "Validating pedestrian trips",
        cwd=config_dir
    )
    print("✅ Pedestrian trips validated successfully")

    # Step 9: Generate pedestrian routes
    print_step(9, "Generating pedestrian routes [pedestrians.rou.xml]")
    run_command(
        "duarouter --net-file mynet.net.xml --route-files pedestrians.trips.xml --output-file pedestrians.rou.xml --alternatives-output NUL --ignore-errors",
        "Generating pedestrian routes",
        cwd=config_dir
    )
    print("✅ Pedestrian routes generated successfully")

    # Step 10: Create configuration file
    print_step(10, "Creating configuration file [myconfig.sumocfg]")
    config_content = '''<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="mynet.net.xml"/>
        <route-files value="vehicles.rou.xml,pedestrians.rou.xml"/>
        <additional-files value="vehicle_types.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="1000"/>
    </time>
</configuration>'''
    
    with open(config_dir / "myconfig.sumocfg", "w") as f:
        f.write(config_content)
    
    print("✅ Configuration file created successfully")

    # Step 11: Remove any existing routes.rou.xml
    print_step(11, "Cleaning up existing routes.rou.xml")
    routes_file = config_dir / "routes.rou.xml"
    if routes_file.exists():
        routes_file.unlink()
        print("✅ Removed existing routes.rou.xml")
    else:
        print("ℹ️ No existing routes.rou.xml found")

    # Step 12: Verify simulation setup
    print_step(12, "Verifying simulation setup")
    run_command(
        "sumo --net-file mynet.net.xml --route-files vehicles.rou.xml --no-step-log true --quit-on-end true --begin 0 --end 1",
        "Verifying simulation setup",
        cwd=config_dir
    )
    print("✅ Simulation verification passed")

    # Final success message
    print("\n" + "="*60)
    print("🎉 All steps completed successfully!")
    print("="*60)
    print(f"\n📁 All files have been generated in: {config_dir}")
    print("\n📁 Generated files:")
    generated_files = [
        "mynet.net.xml",
        "vehicles.trips.raw.xml",
        "vehicles.trips.xml",
        "vehicles.rou.xml",
        "vehicles.rou.alt.xml",
        "pedestrians.trips.raw.xml",
        "pedestrians.trips.xml",
        "pedestrians.rou.xml",
        "vehicle_types.xml",
        "myconfig.sumocfg"
    ]
    
    for file in generated_files:
        file_path = config_dir / file
        if file_path.exists():
            print(f"\t• ✅ {file}")
        else:
            print(f"\t• ❌ {file} (missing)")
    
    print("\n🎮 You can now run your simulation from the configuration directory:")
    print("\tpython main.py")
    
    print("\n📚 For more information, refer to:")
    print("\t📖 README.md file")
    print("\t🌐 GitHub Repository: https://github.com/vaibhavgarg9/v2x-communication-simulator")
    
    print("\n✨ Happy simulating!")

if __name__ == "__main__":
    main()