import pygame   # Game library; used here for creating the display window

RESTITUTION = 0.75   # Bounciness factor when a ball hits a wall.
                     # 1.0 = perfectly elastic (no energy lost), 0.75 = 25% energy lost per wall bounce.


class Environment:
    """
    Manages the physical space the simulation runs in.
    Responsibilities:
      1. Creating and holding the pygame window (screen)
      2. Bouncing balls off the four walls (boundary conditions)
      3. Efficiently detecting which pairs of balls are close enough to collide,
         using a spatial hash grid to avoid checking every pair (which would be O(n²))
    """

    def __init__(self, width, height, cell_size=100):
        """
        Constructor. Creates the window and sets up the spatial grid.

        Parameters:
            width, height : dimensions of the simulation window in pixels
            cell_size     : size of each grid cell in pixels (for collision broadphase)
        """
        self.width     = width
        self.height    = height
        self.cell_size = cell_size   # Balls further apart than this will never share a grid cell

        # Create the pygame display window at the given size
        self.screen = pygame.display.set_mode((width, height))

        # The spatial hash: a dictionary mapping (cell_x, cell_y) → list of balls in that cell.
        # This is rebuilt every frame in resolve_collisions().
        self.cells = {}

    def apply_boundaries(self, ball):
        """
        Checks whether the ball has gone outside the screen edges.
        If so, it moves the ball back inside and reflects its velocity component.

        Returns:
            hit   (bool)  : True if the ball touched any wall this frame
            speed (float) : the ball's speed at the moment of the check (before reflection)
        """
        hit   = False
        speed = ball.speed   # Record speed before any velocity changes

        # --- Left wall ---
        if ball.x - ball.radius < 0:
            ball.x  = ball.radius         # Move ball so its left edge is exactly at x=0
            ball.vx = abs(ball.vx) * RESTITUTION   # Reflect: ensure vx is positive (rightward), reduce by RESTITUTION
            hit     = True

        # --- Right wall ---
        if ball.x + ball.radius > self.width:
            ball.x  = self.width - ball.radius   # Move ball so its right edge is at the screen edge
            ball.vx = -abs(ball.vx) * RESTITUTION  # Reflect: ensure vx is negative (leftward)
            hit     = True

        # --- Top wall ---
        if ball.y - ball.radius < 0:
            ball.y  = ball.radius
            ball.vy = abs(ball.vy) * RESTITUTION   # Reflect: ensure vy is positive (downward)
            hit     = True

        # --- Bottom wall ---
        if ball.y + ball.radius > self.height:
            ball.y  = self.height - ball.radius
            ball.vy = -abs(ball.vy) * RESTITUTION  # Reflect: ensure vy is negative (upward)
            hit     = True

        return hit, speed

    def clear_grid(self):
        """
        Resets the spatial hash to an empty dictionary.
        Called at the start of every collision-detection pass so the grid reflects current positions.
        """
        self.cells = {}

    def insert(self, ball):
        """
        Inserts a ball into every grid cell it overlaps.
        A ball can overlap up to 4 cells if it straddles cell boundaries.

        The cell a point (x, y) belongs to is simply: (floor(x / cell_size), floor(y / cell_size))
        We use the ball's edges (x ± radius) to find all cells it touches.

        Parameters:
            ball : the Ball object to insert
        """
        # Find the range of grid cells this ball's bounding box spans
        min_cx = int((ball.x - ball.radius) // self.cell_size)   # Leftmost cell column
        max_cx = int((ball.x + ball.radius) // self.cell_size)   # Rightmost cell column
        min_cy = int((ball.y - ball.radius) // self.cell_size)   # Topmost cell row
        max_cy = int((ball.y + ball.radius) // self.cell_size)   # Bottommost cell row

        # Iterate over every cell the ball overlaps and register it there
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                key = (cx, cy)   # Use the cell coordinate pair as the dictionary key
                if key not in self.cells:
                    self.cells[key] = []   # Create a new list for this cell if it doesn't exist yet
                self.cells[key].append(ball)

    def get_nearby(self, ball):
        """
        Returns the set of all other balls that share at least one grid cell with this ball.
        These are the only candidates that could possibly be colliding — balls in distant cells
        are guaranteed to be too far apart to touch.

        Parameters:
            ball : the Ball we want to find neighbours for

        Returns:
            A Python set of Ball objects (never includes `ball` itself)
        """
        min_cx = int((ball.x - ball.radius) // self.cell_size)
        max_cx = int((ball.x + ball.radius) // self.cell_size)
        min_cy = int((ball.y - ball.radius) // self.cell_size)
        max_cy = int((ball.y + ball.radius) // self.cell_size)

        nearby = set()   # A set automatically eliminates duplicates

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                # .get() returns an empty list if the cell has no balls, avoiding a KeyError
                for other in self.cells.get((cx, cy), []):
                    if other is not ball:   # Don't include the ball itself
                        nearby.add(other)

        return nearby

    def resolve_collisions(self, balls):
        """
        Detects and resolves all ball-ball collisions for a given frame.

        Steps:
          1. Rebuild the spatial grid with current ball positions.
          2. For each ball, find nearby candidates via the grid.
          3. For each unique pair, call ball.collide() to resolve the overlap.

        The `checked` set ensures each pair (A, B) is processed exactly once,
        not twice (once as (A,B) and again as (B,A)).

        Parameters:
            balls : the list of all Ball objects in the simulation
        """
        # Step 1: Clear and rebuild the spatial hash grid
        self.clear_grid()
        for ball in balls:
            self.insert(ball)

        # Step 2 & 3: Check each ball against its nearby neighbours
        checked = set()   # Tracks which pairs have already been processed

        for ball in balls:
            for other in self.get_nearby(ball):
                # frozenset creates an unordered pair — frozenset({A,B}) == frozenset({B,A})
                # This ensures the pair is only resolved once
                pair = frozenset((id(ball), id(other)))   # id() gives each object's unique memory address
                if pair not in checked:
                    ball.collide(other)    # Resolve the collision (defined in Ball class)
                    checked.add(pair)      # Mark this pair as done
