"""A wave function collapse image generator."""

# based on https://github.com/mxgmn/WaveFunctionCollapse

from collections import defaultdict
from pathlib import Path
from random import Random

from PIL import Image, ImageOps


class Tile:

    def __init__(self, path, reflected, rotation):
        self.path = path.resolve().expanduser()
        self.image = Image.open(self.path)
        self.reflected = reflected
        self.rotation = rotation
        if reflected:
            self.image = ImageOps.mirror(self.image)
        self.image = self.image.rotate(rotation * 90)
        self.borders = (
            tuple(self.image.getpixel((col, 0)) for col in range(self.width)),
            tuple(self.image.getpixel((0, row)) for row in range(self.height)),
            tuple(self.image.getpixel((col, self.height - 1)) for col in range(self.width)),
            tuple(self.image.getpixel((self.width - 1, row)) for row in range(self.height)),
        )

    @property
    def args(self):
        return (self.path, self.reflected, self.rotation)

    def __eq__(self, other):
        return isinstance(other, Tile) and self.args == other.args

    def __hash__(self):
        return hash(self.args)

    def __lt__(self, other):
        return self.args < other.args

    def __repr__(self):
        return 'Tile(' + ', '.join(repr(arg) for arg in self.args) + ')'

    @property
    def width(self):
        return self.image.width

    @property
    def height(self):
        return self.image.height


class TileSet:

    def __init__(self):
        self.tiles = {}
        self.border_map = (
            defaultdict(set),
            defaultdict(set),
            defaultdict(set),
            defaultdict(set),
        )
        self.tile_width = None
        self.tile_height = None

    def __len__(self):
        return len(self.tiles)

    def add_tile(self, path, weight):
        image = Image.open(str(path))
        if self.tile_width is None:
            self.tile_width = image.width
            self.tile_height = image.height
        elif image.width != self.tile_width:
            raise ValueError('Tiles are not of the same size')
        count = 0
        exists = []
        tiles = set()
        for reflection in (False, True):
            for rotation in range(4):
                tile = Tile(path, reflection, rotation)
                if tile.image in exists:
                    continue
                exists.append(tile.image)
                tiles.add(tile)
        for tile in sorted(tiles):
            self.tiles[tile] = weight / len(tiles)
            for side in range(4):
                self.border_map[side][tile.borders[side]].add(tile)

    def get_weight(self, tile):
        return self.tiles[tile]

    def match_border(self, border, side):
        return set(tile for tile in self.border_map[side][border])


def neighbors(coord, width, height):
    for side, (diff_row, diff_col) in enumerate(((-1, 0), (0, -1), (1, 0), (0, 1))):
        row = coord[0] + diff_row
        col = coord[1] + diff_col
        if 0 <= row < height and 0 <= col < width:
            yield side, (row, col)


def generate_image(width, height, tileset, seed=None, rng=None, image_name=None):

    def place(coord, tile, placed, frontier):
        placed[coord] = tile
        frontier.pop(coord, None)
        for side, frontier_coord in neighbors(coord, width, height):
            if frontier_coord in placed:
                continue
            valid_tiles = tileset.match_border(tile.borders[side], (side + 2) % 4)
            if frontier_coord in frontier:
                frontier[frontier_coord].intersection_update(valid_tiles)
            else:
                frontier[frontier_coord] = valid_tiles
            if len(frontier[frontier_coord]) == 0:
                raise ValueError(f'Constraint failure at {frontier_coord}')

    def save_image(placed, image_name):
        TILE_SIZE = 10
        image = Image.new('RGBA', (width * TILE_SIZE, height * TILE_SIZE))
        for tile_coord, tile in placed.items():
            image.paste(
                tile.image,
                (tile_coord[1] * TILE_SIZE, tile_coord[0] * TILE_SIZE),
            )
        image.save(image_name)

    if rng is None:
        rng = Random(8675309)
    if seed is None:
        seed = {
            (0, 0): rng.choice(sorted(tileset.tiles)),
        }
    placed = {}
    frontier = {}
    for coord, tile in seed.items():
        place(coord, tile, placed, frontier)
    while len(placed) < width * height:
        coord, possibilities = min(frontier.items(), key=(lambda pair: len(pair[1])))
        possibilities = sorted(possibilities)
        weights = [tileset.get_weight(tile) for tile in possibilities]
        place(coord, rng.choices(possibilities, weights=weights)[0], placed, frontier)
    if image_name is None:
        image_name = 'new.png'
    save_image(placed, image_name)


def main():
    tileset = TileSet()
    tileset.add_tile(Path('tilesets/knots/corner.png'), 4)
    tileset.add_tile(Path('tilesets/knots/cross.png'), 2)
    tileset.add_tile(Path('tilesets/knots/empty.png'), 1)
    tileset.add_tile(Path('tilesets/knots/line.png'), 2)
    tileset.add_tile(Path('tilesets/knots/t.png'), 4)
    size = 100
    generate_image(
        size,
        size,
        tileset,
        seed={
            (size // 2, size // 2): Tile(Path('tilesets/knots/cross.png'), False, 0),
        },
    )


if __name__ == '__main__':
    main()
