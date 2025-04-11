# Stellar Forge Simulator

## Description
Develop an endless 2D space exploration sandbox featuring a player-controlled rocket navigating procedurally generated star systems. Utilizes physics simulations for celestial body interactions and simple ML techniques to create diverse planetary characteristics.

## Features
- Procedural generation of unique star systems including stars (suns), planets with random properties (mass, radius, color, basic atmospheric density), and asteroid fields.
- Simplified 2D gravitational physics simulation focusing on dominant gravitational forces (e.g., star on planets, nearby planets/star on the rocket).
- Player-controlled rocket with physics-based movement (thrust application, gravitational pull). Think Kerbal Space Program, but 2D and maybe less explosions... maybe.
- Simple ML model (e.g., a trained Gaussian Mixture Model or regression model using scikit-learn) to generate varied and somewhat plausible physical properties for planets based on orbital distance or other seed parameters.
- Real-time visualization of the space environment and rocket trajectory using Pygame.

## Learning Benefits
Gain hands-on experience implementing 2D physics simulations (gravity, kinematics), mastering procedural content generation techniques for endless environments, integrating machine learning models (even simple ones) into dynamic simulations to add variability, applying vector mathematics practically with NumPy, and understanding the fundamentals of game development loops and rendering with Pygame. It's not just another classification task, it's science!

## Technologies Used
- pygame (for visualization, user input, game loop)
- numpy (for vector math, physics calculations, handling numerical data)
- scikit-learn (for the ML model generating planet properties)
- random (for seeding procedural generation)

## Setup and Installation

```bash
# Clone the repository
git clone https://github.com/Omdeepb69/stellar-forge-simulator.git
cd stellar-forge-simulator

# Install dependencies
pip install -r requirements.txt
```

## Usage
[Instructions on how to use the project]

## Project Structure
[Brief explanation of the project structure]

## License
MIT
