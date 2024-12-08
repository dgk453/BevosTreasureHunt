from enum import Enum
import gymnasium as gym
from gymnasium import spaces
import pygame
import numpy as np

class Actions(Enum):
    right = 0
    up = 1
    left = 2
    down = 3


class GridWorldEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 4}

    def __init__(self, render_mode=None, size=5, max_steps=50, grass_count=3, ou_count=3):
        self.size = size
        self.window_size = 512
        self.max_steps = max_steps
        self.grass_count = grass_count
        self.ou_count = ou_count
        self.observation_space = spaces.Dict({
            "agent": spaces.Box(0, size - 1, shape=(2,), dtype=int),
            "tiles": spaces.Box(-1, 1, shape=(size, size), dtype=int),
        })
        self.action_space = spaces.Discrete(4)
        self._action_to_direction = {
            Actions.right.value: np.array([1, 0]),
            Actions.up.value: np.array([0, 1]),
            Actions.left.value: np.array([-1, 0]),
            Actions.down.value: np.array([0, -1]),
        }
        assert render_mode is None or render_mode in self.metadata["render_modes"]
        self.render_mode = render_mode
        self.window = None
        self.clock = None
        self.grid = None
        self._agent_location = None
        self.steps = 0
        self.score = 10

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        self.score = 10
        self._agent_location = self.np_random.integers(0, self.size, size=2, dtype=int)
        self.grid = np.zeros((self.size, self.size), dtype=int)
        # Place grass (1)
        for _ in range(self.grass_count):
            while True:
                loc = self.np_random.integers(0, self.size, size=2, dtype=int)
                if not np.array_equal(loc, self._agent_location) and self.grid[tuple(loc)] == 0:
                    self.grid[tuple(loc)] = 1
                    break
        # Place ou (hazards) (-1)
        for _ in range(self.ou_count):
            while True:
                loc = self.np_random.integers(0, self.size, size=2, dtype=int)
                if not np.array_equal(loc, self._agent_location) and self.grid[tuple(loc)] == 0:
                    self.grid[tuple(loc)] = -1
                    break
        observation = self._get_obs()
        if self.render_mode == "human":
            self._render_frame()
        return observation

    def step(self, action):
        direction = self._action_to_direction[action]
        self._agent_location = np.clip(self._agent_location + direction, 0, self.size - 1)
        tile_value = self.grid[tuple(self._agent_location)]
        
        # Update score based on the tile the agent moves to
        if tile_value == 1:  # Grass
            self.score += 10
        elif tile_value == -1:  # OU (hazard)
            self.score -= 5
        # Clear the grass or OU from the grid after the agent eats or interacts with it
        self.grid[tuple(self._agent_location)] = 0
        self.steps += 1

        grass_remaining = np.sum(self.grid == 1)
        terminated = self.score < 0 or self.steps >= self.max_steps or grass_remaining == 0

        truncated = False
        observation = self._get_obs()

        if self.render_mode == "human":
            self._render_frame()

        return observation, self.score, terminated, truncated, {}

    def _get_obs(self):
        return {
            "agent": self._agent_location.copy(),
            "tiles": self.grid.copy(),
        }

    def render(self):
        if self.render_mode == "rgb_array":
            return self._render_frame()

    def _render_frame(self):
        if self.window is None and self.render_mode == "human":
            pygame.init()
            pygame.display.init()
            self.window = pygame.display.set_mode(
                (self.window_size, self.window_size + 50))  # Add space for score and steps
        if self.clock is None and self.render_mode == "human":
            self.clock = pygame.time.Clock()

        canvas = pygame.Surface((self.window_size, self.window_size + 50))
        canvas.fill((255, 255, 255))
        pix_square_size = self.window_size // self.size
        grass_image = pygame.image.load("images/grass.png")
        grass_image = pygame.transform.scale(grass_image, (pix_square_size, pix_square_size))
        agent_image = pygame.image.load("images/bevo.png")
        agent_image = pygame.transform.scale(agent_image, (pix_square_size, pix_square_size))
        ou_image = pygame.image.load("images/ou.png")
        ou_image = pygame.transform.scale(ou_image, (pix_square_size, pix_square_size))

        # Draw the grass, ou (hazard), and agent on the canvas
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x, y] == 1:
                    canvas.blit(grass_image, (x * pix_square_size, y * pix_square_size + 50))
                elif self.grid[x, y] == -1:
                    canvas.blit(ou_image, (x * pix_square_size, y * pix_square_size + 50))

        canvas.blit(agent_image,
                    (self._agent_location[0] * pix_square_size, self._agent_location[1] * pix_square_size + 50))

        for x in range(self.size + 1):
            pygame.draw.line(canvas, (0, 0, 0), (0, pix_square_size * x + 50),
                             (self.window_size, pix_square_size * x + 50),
                             width=3)
            pygame.draw.line(canvas, (0, 0, 0), (pix_square_size * x, 50), (pix_square_size * x, self.window_size + 50),
                             width=3)

        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}", True, (0, 0, 0))
        steps_text = font.render(f"Steps: {self.steps}/{self.max_steps}", True, (0, 0, 0))

        canvas.blit(score_text, (10, 10))
        text_width, _ = steps_text.get_size()
        canvas.blit(steps_text, (self.window_size - text_width - 10, 10))

        # Show the canvas in the window
        if self.render_mode == "human":
            self.window.blit(canvas, canvas.get_rect())
            pygame.event.pump()
            pygame.display.update()
            self.clock.tick(self.metadata["render_fps"])
        else:
            return np.transpose(np.array(pygame.surfarray.pixels3d(canvas)), axes=(1, 0, 2))

    def close(self):
        if self.window is not None:
            pygame.display.quit()
            pygame.quit()
