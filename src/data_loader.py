import numpy as np
import random
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

# Constants for synthetic data generation
DEFAULT_NUM_SAMPLES = 2000
MIN_ORBITAL_DISTANCE = 0.1  # Astronomical Units (AU)
MAX_ORBITAL_DISTANCE = 50.0 # AU
MIN_MASS_FACTOR = 0.01      # Earth masses
MAX_MASS_FACTOR = 2000.0    # Earth masses (Gas giants)
MIN_RADIUS_FACTOR = 0.1     # Earth radii
MAX_RADIUS_FACTOR = 20.0      # Earth radii (Gas giants)
MIN_DENSITY = 0.1           # Arbitrary units
MAX_DENSITY = 10.0          # Arbitrary units
DISTANCE_MASS_POWER = 0.5   # Mass tends to increase with distance (gas giants)
DISTANCE_RADIUS_POWER = 0.4 # Radius tends to increase with distance
DISTANCE_DENSITY_POWER = -0.3 # Density tends to decrease with distance
NOISE_LEVEL = 0.2           # Noise factor for properties

DEFAULT_MODEL_FILENAME = 'planet_property_models.pkl'

def generate_synthetic_planet_data(num_samples=DEFAULT_NUM_SAMPLES):
    """
    Generates synthetic data for planet properties based on orbital distance.

    Args:
        num_samples (int): The number of synthetic planet samples to generate.

    Returns:
        tuple: A tuple containing:
            - orbital_distances (np.ndarray): Array of orbital distances (shape: num_samples, 1).
            - properties (np.ndarray): Array of corresponding properties [mass, radius, density]
                                       (shape: num_samples, 3).
    """
    random.seed(42)
    np.random.seed(42)

    # Generate orbital distances (log-uniformly distributed for better spread)
    log_min_dist = np.log(MIN_ORBITAL_DISTANCE)
    log_max_dist = np.log(MAX_ORBITAL_DISTANCE)
    log_distances = np.random.uniform(log_min_dist, log_max_dist, num_samples)
    orbital_distances = np.exp(log_distances)

    # Generate properties based on distance with noise
    # Base values increase/decrease with distance according to power laws
    base_mass = MIN_MASS_FACTOR + (MAX_MASS_FACTOR - MIN_MASS_FACTOR) * \
                ((orbital_distances - MIN_ORBITAL_DISTANCE) / (MAX_ORBITAL_DISTANCE - MIN_ORBITAL_DISTANCE)) ** DISTANCE_MASS_POWER
    base_radius = MIN_RADIUS_FACTOR + (MAX_RADIUS_FACTOR - MIN_RADIUS_FACTOR) * \
                  ((orbital_distances - MIN_ORBITAL_DISTANCE) / (MAX_ORBITAL_DISTANCE - MIN_ORBITAL_DISTANCE)) ** DISTANCE_RADIUS_POWER
    base_density = MAX_DENSITY + (MIN_DENSITY - MAX_DENSITY) * \
                   ((orbital_distances - MIN_ORBITAL_DISTANCE) / (MAX_ORBITAL_DISTANCE - MIN_ORBITAL_DISTANCE)) ** abs(DISTANCE_DENSITY_POWER) # Power is negative

    # Add multiplicative noise (log-normal noise)
    mass_noise = np.random.lognormal(mean=0, sigma=NOISE_LEVEL, size=num_samples)
    radius_noise = np.random.lognormal(mean=0, sigma=NOISE_LEVEL, size=num_samples)
    density_noise = np.random.lognormal(mean=0, sigma=NOISE_LEVEL, size=num_samples)

    mass = base_mass * mass_noise
    radius = base_radius * radius_noise
    density = base_density * density_noise

    # Clip values to reasonable bounds
    mass = np.clip(mass, MIN_MASS_FACTOR * 0.5, MAX_MASS_FACTOR * 1.5)
    radius = np.clip(radius, MIN_RADIUS_FACTOR * 0.5, MAX_RADIUS_FACTOR * 1.5)
    density = np.clip(density, MIN_DENSITY * 0.5, MAX_DENSITY * 1.5)

    properties = np.vstack([mass, radius, density]).T
    orbital_distances = orbital_distances.reshape(-1, 1)

    return orbital_distances, properties

def preprocess_data(X, y):
    """
    Preprocesses the data (currently just placeholder, could add scaling etc.).

    Args:
        X (np.ndarray): Feature data (orbital distances).
        y (np.ndarray): Target data (properties).

    Returns:
        tuple: Preprocessed X and y.
    """
    # No complex preprocessing needed for this synthetic data and simple models yet
    # Could add StandardScaler here if needed
    return X, y

def train_property_models(X, y, test_size=0.2, random_state=42):
    """
    Splits data, trains regression models for each planet property based on orbital distance.

    Args:
        X (np.ndarray): Feature data (orbital distances, shape: num_samples, 1).
        y (np.ndarray): Target data (properties [mass, radius, density], shape: num_samples, 3).
        test_size (float): Proportion of data to use for the test set.
        random_state (int): Random seed for splitting.

    Returns:
        dict: A dictionary containing trained models for 'mass', 'radius', and 'density'.
              Returns None if training fails.
    """
    if X.shape[0] != y.shape[0]:
        raise ValueError("X and y must have the same number of samples.")
    if y.shape[1] != 3:
        raise ValueError("y must have 3 columns (mass, radius, density).")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    models = {}
    property_names = ['mass', 'radius', 'density']

    print("Training planet property models...")
    for i, name in enumerate(property_names):
        print(f"  Training model for: {name}")
        target_train = y_train[:, i]
        target_test = y_test[:, i]

        # Using Gradient Boosting Regressor for potentially better non-linear fits
        # If performance is an issue, LinearRegression can be used as a fallback
        # model = Pipeline([
        #     ('scaler', StandardScaler()), # Scaling is often good for GBR
        #     ('regressor', GradientBoostingRegressor(n_estimators=100, random_state=random_state))
        # ])
        model = GradientBoostingRegressor(n_estimators=100, random_state=random_state)

        try:
            model.fit(X_train, target_train)
            models[name] = model
            # Optional: Evaluate model
            y_pred = model.predict(X_test)
            mse = mean_squared_error(target_test, y_pred)
            print(f"    Model for {name} trained. Test MSE: {mse:.4f}")
        except Exception as e:
            print(f"    Error training model for {name}: {e}")
            return None # Indicate failure

    print("Model training complete.")
    return models

def save_models(models, filename=DEFAULT_MODEL_FILENAME):
    """
    Saves the trained models to a file using pickle.

    Args:
        models (dict): Dictionary of trained models.
        filename (str): Path to save the models file.
    """
    try:
        with open(filename, 'wb') as f:
            pickle.dump(models, f)
        print(f"Models successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving models to {filename}: {e}")

def load_models(filename=DEFAULT_MODEL_FILENAME):
    """
    Loads trained models from a file.

    Args:
        filename (str): Path to the models file.

    Returns:
        dict: Dictionary of loaded models, or None if loading fails or file not found.
    """
    if not os.path.exists(filename):
        print(f"Model file {filename} not found.")
        return None
    try:
        with open(filename, 'rb') as f:
            models = pickle.load(f)
        print(f"Models successfully loaded from {filename}")
        # Basic check if loaded object is a dictionary
        if isinstance(models, dict) and all(k in models for k in ['mass', 'radius', 'density']):
             return models
        else:
            print(f"Error: Loaded file {filename} does not contain the expected model dictionary.")
            return None
    except Exception as e:
        print(f"Error loading models from {filename}: {e}")
        return None

def get_trained_property_models(force_retrain=False, num_synthetic_samples=DEFAULT_NUM_SAMPLES, model_filename=DEFAULT_MODEL_FILENAME):
    """
    Loads pre-trained planet property models or trains them if they don't exist or retraining is forced.

    Args:
        force_retrain (bool): If True, forces retraining even if a model file exists.
        num_synthetic_samples (int): Number of samples for synthetic data generation if training.
        model_filename (str): Filename for saving/loading the models.

    Returns:
        dict: A dictionary containing trained models for 'mass', 'radius', and 'density'.
    """
    models = None
    if not force_retrain:
        models = load_models(model_filename)

    if models is None:
        print("Generating synthetic data for model training...")
        X, y = generate_synthetic_planet_data(num_samples=num_synthetic_samples)
        X_proc, y_proc = preprocess_data(X, y)
        models = train_property_models(X_proc, y_proc)

        if models:
            save_models(models, model_filename)
        else:
            print("Model training failed. Unable to provide property models.")
            # Fallback: return None or raise an error? Returning None for now.
            return None

    return models

# Example usage (can be run standalone to train/save models)
if __name__ == "__main__":
    print("Running data_loader.py standalone to ensure models are trained/available.")

    # Force retraining if you want to regenerate models
    force_retrain_flag = False
    # force_retrain_flag = True # Uncomment to force retraining

    trained_models = get_trained_property_models(force_retrain=force_retrain_flag)

    if trained_models:
        print("\nTesting loaded/trained models:")
        # Example: Predict properties for a planet at 1 AU and 10 AU
        test_distances = np.array([[1.0], [10.0]]) # Needs to be 2D array

        for dist_val in test_distances:
            print(f"\nPredicted properties for distance: {dist_val[0]:.2f} AU")
            try:
                mass_pred = trained_models['mass'].predict(dist_val.reshape(1, -1))[0]
                radius_pred = trained_models['radius'].predict(dist_val.reshape(1, -1))[0]
                density_pred = trained_models['density'].predict(dist_val.reshape(1, -1))[0]
                print(f"  Predicted Mass: {mass_pred:.4f} Earth Masses")
                print(f"  Predicted Radius: {radius_pred:.4f} Earth Radii")
                print(f"  Predicted Density: {density_pred:.4f} units")
            except Exception as e:
                 print(f"  Error during prediction: {e}")
    else:
        print("\nFailed to load or train models.")