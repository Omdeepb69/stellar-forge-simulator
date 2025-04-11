import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

# --- Project Root ---
BASE_DIR = Path(__file__).resolve().parent.parent # Assumes config.py is in a 'config' or similar subfolder

# --- Path Configurations ---
@dataclass
class PathConfig:
    data_dir: Path = BASE_DIR / "data"
    raw_data_dir: Path = data_dir / "raw"
    processed_data_dir: Path = data_dir / "processed"
    output_dir: Path = BASE_DIR / "output"
    model_dir: Path = output_dir / "models"
    log_dir: Path = output_dir / "logs"
    results_dir: Path = output_dir / "results"
    figure_dir: Path = output_dir / "figures"

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.figure_dir.mkdir(parents=True, exist_ok=True)

# --- Model Parameters ---
@dataclass
class ModelParameters:
    # Stellar Evolution Model
    stellar_mass_min: float = 0.1  # Solar masses
    stellar_mass_max: float = 100.0 # Solar masses
    metallicity: float = 0.012 # Z, solar metallicity ~0.012-0.02
    initial_mass_function: str = "salpeter" # Options: 'salpeter', 'kroupa'
    timestep_resolution: float = 1e6 # Years

    # Star Formation Model
    star_formation_efficiency: float = 0.02
    gas_density_threshold: float = 100.0 # particles/cm^3

    # Supernova Feedback Model
    supernova_energy: float = 1e51 # ergs
    feedback_radius: float = 50.0 # parsecs

    # Simulation Grid / Domain
    grid_resolution: int = 256 # Number of cells per dimension
    domain_size: float = 1000.0 # parsecs

# --- Training Parameters (Example - if ML components are used) ---
@dataclass
class TrainingParameters:
    learning_rate: float = 1e-4
    batch_size: int = 64
    num_epochs: int = 100
    validation_split: float = 0.2
    optimizer: str = "adam" # Options: 'adam', 'sgd', 'rmsprop'
    loss_function: str = "mean_squared_error"
    early_stopping_patience: int = 10
    use_gpu_if_available: bool = True
    seed: int = 42

# --- Environment Configuration ---
@dataclass
class EnvironmentConfig:
    log_level: int = logging.INFO # logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file_name: str = "stellar_forge_simulator.log"
    random_seed: int = 42
    num_workers: int = os.cpu_count() or 1 # Default to number of CPU cores

# --- Main Configuration Class ---
@dataclass
class AppConfig:
    project_name: str = "Stellar Forge Simulator"
    version: str = "0.1.0"
    paths: PathConfig = field(default_factory=PathConfig)
    model: ModelParameters = field(default_factory=ModelParameters)
    training: TrainingParameters = field(default_factory=TrainingParameters)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)

# --- Instantiate Configuration ---
config = AppConfig()

# --- Example Usage (can be removed in final deployment) ---
if __name__ == "__main__":
    print("--- Configuration Loaded ---")
    print(f"Project Name: {config.project_name} v{config.version}")

    print("\n--- Paths ---")
    print(f"Data Directory: {config.paths.data_dir}")
    print(f"Model Directory: {config.paths.model_dir}")
    print(f"Log Directory: {config.paths.log_dir}")

    print("\n--- Model Parameters ---")
    print(f"Min Stellar Mass: {config.model.stellar_mass_min}")
    print(f"IMF: {config.model.initial_mass_function}")
    print(f"Grid Resolution: {config.model.grid_resolution}")

    print("\n--- Training Parameters ---")
    print(f"Learning Rate: {config.training.learning_rate}")
    print(f"Batch Size: {config.training.batch_size}")
    print(f"Seed: {config.training.seed}")

    print("\n--- Environment Configuration ---")
    print(f"Log Level: {logging.getLevelName(config.environment.log_level)}")
    print(f"Log File: {config.paths.log_dir / config.environment.log_file_name}")
    print(f"Number of Workers: {config.environment.num_workers}")

    # Setup basic logging based on config for demonstration
    log_file_path = config.paths.log_dir / config.environment.log_file_name
    logging.basicConfig(
        level=config.environment.log_level,
        format=config.environment.log_format,
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Configuration loaded and logger initialized.")
    logger.debug("This is a debug message.")
    logger.warning("This is a warning message.")