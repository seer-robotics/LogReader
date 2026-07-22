# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LogReader is a PyQt5-based GUI application for analyzing robot log files. It parses structured log data from robots, visualizes trajectories on maps, plots sensor data, and provides error analysis tools.

## Development Environment

- **Python Version**: 3.9.12 (recommended, use Anaconda)
- **Main Dependencies**: PyQt5, matplotlib, numpy, roboticstoolbox-python
- **Install**: `pip install -r requirements.txt`

## Running the Application

```bash
# Run the GUI application
python loggui.py

# Run report generation script
python get_report.py <log_file_1> <log_file_2>
```

## Building Executable

```bash
# Build with spec file (recommended)
pyinstaller loggui.spec

# Or build directly
pyinstaller -w loggui.py

# If font encoding errors occur, run first:
chcp 65001

# After building, copy images/ folder to dist/loggui/
```

## Architecture

### Core Components

**Log Parsing Layer**:
- `loglib.py`: Base log parsing with regex-based `ReadLog` and `Data` classes
- `loglibPlus.py`: Extended parsing with multi-threading support, specialized data types (ErrorLine, WarningLine, FatalLine, NoticeLine, TaskStart, TaskFinish, Service, Laser, Memory, etc.)
- `log_config.json`: Large JSON configuration defining all log parsing rules and data field structures

**Threading & Data Loading**:
- `ReadThread.py`: QThread-based asynchronous log reading, initializes all data parsers, manages multi-threaded parsing (default 4 threads)
- Emits signals to update GUI when parsing completes

**GUI Components**:
- `loggui.py`: Main application window, contains MFTimeCostViewer for time cost analysis
- `MapWidget.py`: Map visualization with robot trajectory, laser data, obstacles, uses matplotlib with custom toolbar
- `LogViewer.py`: Text-based log viewer
- `JsonView.py`: JSON data viewer with DataView for tabular display
- `MyToolBar.py`: Custom matplotlib toolbar with ruler functionality (RulerShape, RulerShapeMap)
- `Widget.py`: Base widget class
- `ExtendedComboBox.py`: Enhanced combo box with search/filter

**Specialized Viewers**:
- `getMotorErr.py`: Motor error analysis (MotorErrViewer)
- `TargetPrecision.py`: Target precision analysis
- `ArmPlot.py`: Robotics arm visualization using robotics-toolbox-python
- `MotorRead.py`: Motor data reading utilities

### Data Flow

1. User selects log files in GUI
2. `ReadThread` spawns, reads files (supports .log, .gz and .zst)
3. Files parsed using regex patterns from `log_config.json`
4. Data stored in `Data` objects (one per log type: mcl, odo, imu, etc.)
5. GUI components subscribe to data updates via Qt signals
6. Matplotlib widgets render visualizations

### Log Data Types

The application parses and visualizes:
- **Localization**: mcl.x, mcl.y, mcl.theta, mcl.confidence
- **Odometry**: odo.x, odo.y, odo.theta, odo.vx, odo.vy, odo.vw, odo.steer_angle, odo.encode0-3
- **IMU**: imu.yaw, imu.pitch, imu.roll, imu.ax, imu.ay, imu.gz, imu.gx, imu.gy, imu.offx, imu.offy, imu.offz
- **Velocity Commands**: send.vx, send.vy, send.vw, send.steer_angle, send.max_vx, send.max_vw
- **Velocity Feedback**: get.vx, get.vy, get.vw, get.steer_angle, get.max_vx, get.max_vw
- **Laser**: laser.ts, laserOdo.ts, laserOdo.x, laserOdo.y, laserOdo.angle
- **Battery**: battery.percentage, battery.current, battery.voltage, battery.ischarging, battery.temperature, battery.cycle
- **Controller**: controller.tmp, controller.humi, controller.emc, controller.brake, etc.
- **Obstacles**: stop.x, stop.y, stop.type, stop.id, stop.dist (blocking obstacles)
- **Obstacles**: slowdown.x, slowdown.y, slowdown.type, slowdown.id, slowdown.dist (slowdown obstacles)
- **Sensor Fusion**: sensorfuser.localnum, sensorfuser.globalnum
- **Logs**: error, warning, fatal, notice lines with timestamps

## Key Implementation Details

### Matplotlib Backend
- Uses Qt5Agg backend: `matplotlib.use('Qt5Agg')`
- Chinese font support: `matplotlib.rcParams['font.sans-serif']=['FangSong']`

### Multi-threading
- Log parsing uses multiprocessing.Pool for parallel processing
- Default 4 worker threads (configurable via `thread_num`)
- Each thread processes a chunk of log lines

### Coordinate Transformations
- `MapWidget.py` contains utilities for coordinate frame transformations:
  - `GetGlobalPos()`: Point from body to global frame
  - `P2G()`: Pose from body to global frame
  - `Pos2Base()`: Pose from world to base frame
  - `convert2LaserPoints()`: Transform laser points to global frame

### Time Handling
- Uses matplotlib date conversion: `date2num()` and `num2date()`
- Supports two timestamp formats: `'%y%m%d %H%M%S.%f'` and `'%Y-%m-%d %H:%M:%S.%f'`
- Time range filtering via `findrange()` function

## Robotics Arm (Optional Feature)

Based on [Robotics Toolbox for Python](https://github.com/petercorke/robotics-toolbox-python):
- Requires roboticstoolbox-python==1.1.1
- On Windows with Swift 3D display, modify `SwiftRoute.py` line 390:
  - Change: `self.path = urllib.parse.unquote(self.path[9:])`
  - To: `self.path = urllib.parse.unquote(self.path[10:])`
- Add custom URDF models to `Lib\site-packages\rtbdata`
- Load models in `Lib\site-packages\roboticstoolbox\models\URDF\seerArm.py`

## Important Files

- `log_config.json`: **Very large file** (62k+ tokens), defines all parsing rules - avoid reading entire file
- `robot.model`: Robot model file for map visualization
- `ErrTab.json`: Error code lookup table
- `loggui.spec`: PyInstaller build specification
- `.gitignore`: Excludes dist/, __pycache__, *.pyc, etc.

## Working with log_config.json

This file is extremely large and defines the structure for parsing all log types. When modifying:
- Use `Read` with `offset` and `limit` parameters to read specific sections
- Or use `Grep` to search for specific log type definitions
- Structure: JSON array of objects with `type` and `content` fields
- Each `content` defines field names, types, regex patterns, units, descriptions
