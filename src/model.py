import os
import random
import joblib
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import silhouette_score # Using silhouette for GMM component evaluation is also an option
import warnings

# Ignore convergence warnings from GMM fitting, common during search
warnings.filterwarnings("ignore", category=UserWarning, module='sklearn.mixture._base')
warnings.filterwarnings("ignore", category=RuntimeWarning, message='invalid value encountered in log') # For BIC calculation issues

# --- Constants ---
MODEL_DIR = "stellar_forge_model"
MODEL_FILE = os.path.join(MODEL_DIR, "planet_gmm_model.joblib")
SCALER_FILE = os.path.join(MODEL_DIR, "planet_scaler.joblib")
DISTRIBUTIONS_FILE = os.path.join(MODEL_DIR, "planet_distributions.joblib")
SYNTHETIC_DATA_SIZE = 5000
RANDOM_SEED = 42
MIN_COMPONENTS = 2
MAX_COMPONENTS = 8 # Max number of planet types/zones to try

# Define plausible property ranges for synthetic data generation and sampling constraints
# Units: distance (AU), mass (Earth masses), radius (Earth radii), density (g/cm^3)
# Color (RGB 0-255)
PROPERTY_RANGES = {
    # Zone 0: Inner Rocky/Hot
    0: {
        'distance': (0.1, 1.5),
        'mass': (0.1, 5.0),
        'radius': (0.4, 1.8),
        'density': (3.5, 6.0),
        'color_mean': [180, 150, 120], # Brownish/Grey
        'color_std': [30, 30, 30]
    },
    # Zone 1: Habitable Zone / Super-Earths
    1: {
        'distance': (0.8, 2.5),
        'mass': (0.5, 15.0),
        'radius': (0.8, 3.0),
        'density': (3.0, 5.5),
        'color_mean': [100, 150, 200], # Bluish/Greenish
        'color_std': [40, 40, 40]
    },
    # Zone 2: Gas Giants
    2: {
        'distance': (3.0, 15.0),
        'mass': (50.0, 2000.0),
        'radius': (5.0, 15.0),
        'density': (0.5, 2.0),
        'color_mean': [200, 180, 150], # Orangey/Tan
        'color_std': [30, 40, 40]
    },
    # Zone 3: Ice Giants / Outer Planets
    3: {
        'distance': (10.0, 50.0),
        'mass': (10.0, 100.0),
        'radius': (3.0, 8.0),
        'density': (1.0, 2.5),
        'color_mean': [150, 200, 220], # Light Blue/Cyan
        'color_std': [30, 30, 30]
    },
     # Zone 4: Distant Icy Bodies / Dwarf Planets
    4: {
        'distance': (30.0, 100.0),
        'mass': (0.01, 1.0),
        'radius': (0.1, 0.8),
        'density': (1.5, 3.0),
        'color_mean': [210, 210, 230], # Pale Grey/White
        'color_std': [20, 20, 20]
    }
}

MIN_PROPERTY_VALUES = {
    'mass': 0.01,
    'radius': 0.1,
    'density': 0.1
}

# --- Synthetic Data Generation ---

def generate_synthetic_planet_data(n_samples=SYNTHETIC_DATA_SIZE, seed=RANDOM_SEED):
    """Generates synthetic data linking orbital distance to planet properties."""
    np.random.seed(seed)
    random.seed(seed)

    features = []
    labels = [] # Keep track of the zone used for generation

    num_zones = len(PROPERTY_RANGES)
    samples_per_zone = n_samples // num_zones

    all_data = []

    for zone_idx, props in PROPERTY_RANGES.items():
        dist_min, dist_max = props['distance']
        mass_min, mass_max = props['mass']
        rad_min, rad_max = props['radius']
        dens_min, dens_max = props['density']
        color_mean = np.array(props['color_mean'])
        color_std = np.array(props['color_std'])

        # Generate orbital distances within the zone's range, adding some overlap/noise
        distances = np.random.uniform(dist_min * 0.8, dist_max * 1.2, samples_per_zone)

        for dist in distances:
            # Generate properties based loosely on ranges (using normal dist around midpoint)
            mass = np.random.normal(loc=(mass_min + mass_max) / 2, scale=(mass_max - mass_min) / 4)
            radius = np.random.normal(loc=(rad_min + rad_max) / 2, scale=(rad_max - rad_min) / 4)
            density = np.random.normal(loc=(dens_min + dens_max) / 2, scale=(dens_max - dens_min) / 4)

            # Generate color
            color = np.random.normal(loc=color_mean, scale=color_std)
            color = np.clip(color, 0, 255).astype(int)

            # Ensure minimum values
            mass = max(MIN_PROPERTY_VALUES['mass'], mass)
            radius = max(MIN_PROPERTY_VALUES['radius'], radius)
            density = max(MIN_PROPERTY_VALUES['density'], density)

            all_data.append([dist, mass, radius, density, color[0], color[1], color[2], zone_idx])

    data_array = np.array(all_data)
    np.random.shuffle(data_array) # Shuffle the combined data

    # Separate features (distance only for GMM input) and full properties
    orbital_distances = data_array[:, 0:1] # Keep as 2D array for scaler
    full_properties = data_array[:, :] # Includes distance, properties, color, and original zone label

    return orbital_distances, full_properties

# --- Model Training ---

def train_planet_model(n_samples=SYNTHETIC_DATA_SIZE, retrain=False):
    """
    Trains a Gaussian Mixture Model to cluster orbital distances and calculates
    property distributions for each cluster. Saves the model, scaler, and distributions.
    """
    print("Starting planet model training...")
    if not retrain and os.path.exists(MODEL_FILE):
        print(f"Model file found at {MODEL_FILE}. Skipping training. Use retrain=True to force.")
        return load_planet_model()

    # 1. Generate Data
    print(f"Generating {n_samples} synthetic data points...")
    orbital_distances, full_properties = generate_synthetic_planet_data(n_samples)

    # 2. Scale Orbital Distance Feature
    print("Scaling orbital distance data...")
    scaler = StandardScaler()
    scaled_distances = scaler.fit_transform(orbital_distances)

    # 3. Hyperparameter Tuning (Find best n_components using BIC)
    print(f"Finding optimal number of components ({MIN_COMPONENTS}-{MAX_COMPONENTS}) using BIC...")
    best_gmm = None
    best_bic = np.inf
    best_n_components = -1

    possible_n_components = range(MIN_COMPONENTS, MAX_COMPONENTS + 1)
    bics = []

    for n_components in possible_n_components:
        try:
            gmm = GaussianMixture(n_components=n_components, random_state=RANDOM_SEED, covariance_type='full', n_init=5)
            gmm.fit(scaled_distances)
            bic = gmm.bic(scaled_distances)
            bics.append(bic)
            print(f"  Components: {n_components}, BIC: {bic:.2f}")
            if bic < best_bic:
                best_bic = bic
                best_gmm = gmm
                best_n_components = n_components
        except Exception as e:
            print(f"  Error fitting GMM with {n_components} components: {e}")
            bics.append(np.inf) # Penalize failures

    if best_gmm is None:
        raise RuntimeError("Failed to find a suitable GMM model. Check data or component range.")

    print(f"Best number of components found: {best_n_components} (BIC: {best_bic:.2f})")

    # 4. Assign data points to final clusters
    print("Assigning data points to final clusters...")
    cluster_labels = best_gmm.predict(scaled_distances)

    # 5. Calculate Property Distributions per Cluster
    print("Calculating property distributions for each cluster...")
    property_distributions = {}
    num_clusters = best_gmm.n_components

    for i in range(num_clusters):
        cluster_mask = (cluster_labels == i)
        cluster_data = full_properties[cluster_mask]

        if len(cluster_data) < 2: # Need at least 2 points to calculate std dev
             print(f"Warning: Cluster {i} has < 2 data points. Using default/broad distributions.")
             # Fallback to some default or average properties if a cluster is too small
             property_distributions[i] = {
                'count': len(cluster_data),
                'mass': {'mean': 1.0, 'std': 0.5},
                'radius': {'mean': 1.0, 'std': 0.5},
                'density': {'mean': 3.0, 'std': 1.0},
                'color': {'mean': [150, 150, 150], 'std': [50, 50, 50]}
             }
             continue

        # Calculate mean and std dev for numerical properties
        mass_mean, mass_std = np.mean(cluster_data[:, 1]), np.std(cluster_data[:, 1])
        radius_mean, radius_std = np.mean(cluster_data[:, 2]), np.std(cluster_data[:, 2])
        density_mean, density_std = np.mean(cluster_data[:, 3]), np.std(cluster_data[:, 3])

        # Calculate mean and std dev for color (RGB)
        color_mean = np.mean(cluster_data[:, 4:7], axis=0)
        color_std = np.std(cluster_data[:, 4:7], axis=0)

        # Ensure std dev is not zero or too small to avoid issues with sampling
        min_std_dev = 1e-3
        mass_std = max(mass_std, min_std_dev * mass_mean) if mass_mean > 0 else min_std_dev
        radius_std = max(radius_std, min_std_dev * radius_mean) if radius_mean > 0 else min_std_dev
        density_std = max(density_std, min_std_dev * density_mean) if density_mean > 0 else min_std_dev
        color_std = np.maximum(color_std, min_std_dev * color_mean)
        color_std = np.maximum(color_std, 1.0) # Ensure minimum color variance

        property_distributions[i] = {
            'count': len(cluster_data),
            'mass': {'mean': mass_mean, 'std': mass_std},
            'radius': {'mean': radius_mean, 'std': radius_std},
            'density': {'mean': density_mean, 'std': density_std},
            'color': {'mean': color_mean.tolist(), 'std': color_std.tolist()}
        }
        print(f"  Cluster {i}: Count={len(cluster_data)}, Mass={mass_mean:.2f}±{mass_std:.2f}, Radius={radius_mean:.2f}±{radius_std:.2f}")


    # 6. Save Model, Scaler, and Distributions
    print("Saving model, scaler, and property distributions...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(best_gmm, MODEL_FILE)
    joblib.dump(scaler, SCALER_FILE)
    joblib.dump(property_distributions, DISTRIBUTIONS_FILE)
    print(f"Model artifacts saved to directory: {MODEL_DIR}")

    return best_gmm, scaler, property_distributions

# --- Model Loading ---

def load_planet_model():
    """Loads the trained GMM, scaler, and property distributions."""
    print("Loading planet model artifacts...")
    if not all(os.path.exists(f) for f in [MODEL_FILE, SCALER_FILE, DISTRIBUTIONS_FILE]):
        print("Model files not found. Please train the model first.")
        return None, None, None

    try:
        gmm_model = joblib.load(MODEL_FILE)
        scaler = joblib.load(SCALER_FILE)
        property_distributions = joblib.load(DISTRIBUTIONS_FILE)
        print("Model, scaler, and distributions loaded successfully.")
        return gmm_model, scaler, property_distributions
    except Exception as e:
        print(f"Error loading model artifacts: {e}")
        return None, None, None

# --- Prediction / Property Generation ---

def generate_planet_properties(orbital_distance, gmm_model, scaler, property_distributions):
    """
    Generates plausible planet properties based on orbital distance using the trained model.

    Args:
        orbital_distance (float): The orbital distance (e.g., in AU).
        gmm_model: The loaded GaussianMixture model.
        scaler: The loaded StandardScaler.
        property_distributions (dict): The loaded dictionary of property distributions per cluster.

    Returns:
        dict: A dictionary containing generated 'mass', 'radius', 'density', 'color' (tuple),
              or None if the model is not loaded.
    """
    if not all([gmm_model, scaler, property_distributions]):
        print("Error: Model components not loaded.")
        # Return some default values maybe? Or raise error? Returning None for now.
        return None

    # Prepare input distance (needs to be 2D array)
    distance_scaled = scaler.transform(np.array([[orbital_distance]]))

    # Predict the most likely cluster/zone for this distance
    cluster_label = gmm_model.predict(distance_scaled)[0]

    # Get the distributions for the predicted cluster
    if cluster_label not in property_distributions:
        print(f"Warning: Predicted cluster label {cluster_label} not found in distributions. Using cluster 0.")
        cluster_label = 0 # Fallback to a default cluster if something went wrong

    dist_data = property_distributions[cluster_label]

    # Sample properties from the cluster's distributions using normal distribution
    mass = np.random.normal(loc=dist_data['mass']['mean'], scale=dist_data['mass']['std'])
    radius = np.random.normal(loc=dist_data['radius']['mean'], scale=dist_data['radius']['std'])
    density = np.random.normal(loc=dist_data['density']['mean'], scale=dist_data['density']['std'])

    # Sample color
    color_mean = np.array(dist_data['color']['mean'])
    color_std = np.array(dist_data['color']['std'])
    color_raw = np.random.normal(loc=color_mean, scale=color_std)
    color = tuple(np.clip(color_raw, 0, 255).astype(int))

    # Apply minimum value constraints
    mass = max(MIN_PROPERTY_VALUES['mass'], mass)
    radius = max(MIN_PROPERTY_VALUES['radius'], radius)
    density = max(MIN_PROPERTY_VALUES['density'], density)

    return {
        'mass': mass,
        'radius': radius,
        'density': density,
        'color': color,
        'type_label': cluster_label # Optionally return the cluster label
    }

# --- Main Execution Block ---

if __name__ == "__main__":
    print("--- Stellar Forge Simulator Model Script ---")

    # Option 1: Train the model (or retrain)
    # Set retrain=True if you want to force retraining even if files exist
    FORCE_RETRAIN = False
    try:
        gmm, scaler, distributions = train_planet_model(n_samples=10000, retrain=FORCE_RETRAIN) # Use more samples for better training
    except Exception as e:
        print(f"\nAn error occurred during training: {e}")
        gmm, scaler, distributions = None, None, None # Ensure variables are None on failure

    # Option 2: Load the existing model (if training was skipped or failed, try loading)
    if not all([gmm, scaler, distributions]):
        print("\nAttempting to load existing model...")
        gmm, scaler, distributions = load_planet_model()

    # Demonstrate property generation if model is loaded
    if all([gmm, scaler, distributions]):
        print("\n--- Generating Example Planet Properties ---")
        test_distances = [0.5, 1.0, 5.0, 15.0, 40.0, 80.0]
        for dist in test_distances:
            properties = generate_planet_properties(dist, gmm, scaler, distributions)
            if properties:
                print(f"Distance: {dist:.2f} AU -> Type: {properties['type_label']}, "
                      f"Mass: {properties['mass']:.2f}, Radius: {properties['radius']:.2f}, "
                      f"Density: {properties['density']:.2f}, Color: {properties['color']}")
            else:
                print(f"Could not generate properties for distance: {dist:.2f} AU")
    else:
        print("\nModel could not be trained or loaded. Cannot generate properties.")
        print("Run the script again to train the model.")

    print("\n--- Model Script Finished ---")