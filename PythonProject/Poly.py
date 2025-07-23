import pygame
import sys
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

pygame.init()
WIDTH, HEIGHT = 1120, 630
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Polygon Operations")
clock = pygame.time.Clock()

backgroundColor = (225, 225, 225)
polygonColor = (100, 100, 100, 180)
borderColor = (0, 0, 0)
statusColor = (25, 158, 194)
highlightColor = (255, 0, 0, 180)
hoverColor = (127, 205, 51)
textColor = (255, 255, 255)
errorColor = (222, 32, 34)
grayNSU = (67, 67, 67)

polygons = []
currentPoly = []
resultPoly = None
operationText = ""
errorMessage = ""
errorTime = 0
history = []
showHelp = False

font = pygame.font.SysFont("colibri", 32)
error_font = pygame.font.SysFont("colibri", 32)

buttonRect = pygame.Rect(10, 5, 100, 30)

def draw_top_panel(surface):
    pygame.draw.rect(surface, (40, 40, 40), (0, 0, WIDTH, 40))
    pygame.draw.rect(surface, grayNSU, buttonRect, border_radius=5)
    top_panel_text = font.render("Help", True, (255, 255, 255))
    surface.blit(top_panel_text, (buttonRect.x + 25, buttonRect.y + 5))

def save_state():
    copied = []
    for p in polygons:
        copied.append({
            'points': p['points'][:],
            'poly': p['poly'],
            'selected': p['selected']
        })
    history.append(copied)

def draw_polygon_fill(surface, poly, polygon_color):
    if poly.geom_type == 'Polygon':
        exterior = list(poly.exterior.coords)
        if len(exterior) > 1:
            temp_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(temp_surf, polygon_color, exterior)
            surface.blit(temp_surf, (0, 0))
        for interior in poly.interiors:
            coordinates = list(interior.coords)
            if len(coordinates) > 1:
                temp_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(temp_surf, (*backgroundColor, 255), coordinates)
                surface.blit(temp_surf, (0, 0))
    elif poly.geom_type == 'MultiPolygon':
        for p in poly.geoms:
            draw_polygon_fill(surface, p, polygon_color)

def draw_polygon_outline(surface, poly, polygon_color):
    if poly.geom_type == 'Polygon':
        exterior = list(poly.exterior.coords)
        if len(exterior) > 1:
            pygame.draw.lines(surface, polygon_color, True, exterior, 2)
        for interior in poly.interiors:
            coordinates = list(interior.coords)
            if len(coordinates) > 1:
                pygame.draw.lines(surface, polygon_color, True, coordinates, 2)
    elif poly.geom_type == 'MultiPolygon':
        for p in poly.geoms:
            draw_polygon_outline(surface, p, polygon_color)

def get_polygon_at_pos(pos):
    poly_point = Point(pos)
    for i, poly_data in enumerate(reversed(polygons)):
        if poly_data['poly'].contains(poly_point):
            return len(polygons) - 1 - i
    return -1

def show_error(msg):
    global errorMessage, errorTime
    errorMessage = msg
    errorTime = pygame.time.get_ticks()

def apply_union():
    global polygons, resultPoly, operationText
    selected = [p for p in polygons if p['selected']]
    if len(selected) < 2:
        show_error("At least 2 polygons must be selected for union")
        return
    save_state()

    union_result = unary_union([p['poly'] for p in selected])

    polygons = [p for p in polygons if not p['selected']]

    if not union_result.is_empty:
        polygons.append({'points': [], 'poly': union_result, 'selected': False})

    operationText = "union"
    resultPoly = None

def apply_intersection():
    global polygons, resultPoly, operationText
    selected = [p for p in polygons if p['selected']]
    if len(selected) < 2:
        show_error("At least 2 polygons must be selected for intersection")
        return
    save_state()
    result = selected[0]['poly']
    for p in selected[1:]:
        result = result.intersection(p['poly'])
        if result.is_empty:
            show_error("Intersection is empty")
            return

    polygons = [p for p in polygons if not p['selected']]

    if result.geom_type == 'Polygon':
        new_points = list(result.exterior.coords)[:-1]
        polygons.append({'points': new_points, 'poly': result, 'selected': False})
    elif result.geom_type == 'MultiPolygon':
        for part in result.geoms:
            new_points = list(part.exterior.coords)[:-1]
            polygons.append({'points': new_points, 'poly': part, 'selected': False})
    operationText = "intersection"
    resultPoly = None

def apply_difference():
    global polygons, resultPoly, operationText
    selected = [p for p in polygons if p['selected']]
    if len(selected) < 2:
        show_error("At least 2 polygons must be selected for difference")
        return
    save_state()

    new_polygons = []
    polygons = [p for p in polygons if not p['selected']]

    for i, base in enumerate(selected):
        others = [p['poly'] for j, p in enumerate(selected) if j != i]
        others_union = unary_union(others)
        diff = base['poly'].difference(others_union)
        if diff.is_empty:
            continue
        if diff.geom_type == 'Polygon':
            new_polygons.append({'points': [], 'poly': diff, 'selected': False})
        elif diff.geom_type == 'MultiPolygon':
            for part in diff.geoms:
                new_polygons.append({'points': [], 'poly': part, 'selected': False})

    polygons.extend(new_polygons)
    operationText = "difference"
    resultPoly = None

def apply_clear():
    global polygons, resultPoly, operationText
    if polygons:
        save_state()
    polygons.clear()
    resultPoly = None
    operationText = "cleared"

def apply_reset():
    global resultPoly, operationText
    resultPoly = None
    operationText = ""

running = True
while running:
    current_time = pygame.time.get_ticks()
    mouse_pos = pygame.mouse.get_pos()
    hover_index = get_polygon_at_pos(mouse_pos) if not currentPoly else -1

    if errorMessage and current_time - errorTime > 3000:
        errorMessage = ""

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if buttonRect.collidepoint(event.pos):
                    showHelp = not showHelp
                    continue

                mods = pygame.key.get_mods()
                ctrl_held = mods & pygame.KMOD_CTRL

                if currentPoly:
                    currentPoly.append(mouse_pos)
                else:
                    if ctrl_held and hover_index != -1:
                        polygons[hover_index]['selected'] = not polygons[hover_index]['selected']
                    else:
                        history.clear()
                        currentPoly = [mouse_pos]

            elif event.button == 3:
                if currentPoly and len(currentPoly) > 2:
                    try:
                        poly_obj = Polygon(currentPoly + [currentPoly[0]])
                        if poly_obj.is_valid:
                            polygons.append({
                                'points': currentPoly.copy(),
                                'poly': poly_obj,
                                'selected': False
                            })
                        else:
                            show_error("Invalid polygon")
                    except Exception as e:
                        show_error(f"Error: {str(e)}")
                currentPoly = []

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                currentPoly = []
            elif event.key == pygame.K_DELETE:
                polygons = [p for p in polygons if not p['selected']]
                resultPoly = None
                operationText = ""
            elif event.key == pygame.K_u:
                apply_union()
            elif event.key == pygame.K_i:
                apply_intersection()
            elif event.key == pygame.K_d:
                apply_difference()
            elif event.key == pygame.K_c:
                apply_clear()
            elif event.key == pygame.K_r:
                if history:
                    polygons = history.pop()
                    resultPoly = None
                    operationText = "undo last operation"
                else:
                    operationText = "nothing to undo"

    screen.fill(backgroundColor)

    alpha_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    mods = pygame.key.get_mods()
    ctrl_held = mods & pygame.KMOD_CTRL

    for i, poly_data in enumerate(polygons):
        is_hover = (i == hover_index)
        if poly_data['selected']:
            color = highlightColor
        elif is_hover and ctrl_held:
            color = hoverColor
        else:
            color = polygonColor
        draw_polygon_fill(alpha_surface, poly_data['poly'], color)

    screen.blit(alpha_surface, (0, 0))

    if resultPoly and not resultPoly.is_empty:
        draw_polygon_outline(screen, resultPoly, borderColor)

    for poly_data in polygons:
        draw_polygon_outline(screen, poly_data['poly'], borderColor)

    if currentPoly:
        if len(currentPoly) > 1:
            pygame.draw.lines(screen, borderColor, False, currentPoly, 2)
        for point in currentPoly:
            pygame.draw.circle(screen, borderColor, point, 5)
        pygame.draw.line(screen, grayNSU, currentPoly[-1], mouse_pos, 1)

    info_text = [
        "LMB: add polygon point",
        "RMB: finish polygon",
        "ESC: cancel polygon drawing",
        "Delete: delete selected polygons",
        "U: union  I: intersection  D: difference",
        "C: clear all",
        "R: undo last operation",
        "Ctrl + LMB: select polygon"
    ]

    if showHelp:
        help_surface = pygame.Surface((420, 250), pygame.SRCALPHA)
        help_surface.fill((67,67,67, 200))

        for i, text in enumerate(info_text):
            text_surf = font.render(text, True, textColor)
            help_surface.blit(text_surf, (10, 10 + i * 30))

        screen.blit(help_surface, (10, 50))

    if operationText:
        op_surf = font.render(f"Operation: {operationText}", True, (90, 145, 36))
        screen.blit(op_surf, (WIDTH - op_surf.get_width() - 10, 60))

    if errorMessage:
        error_surf = error_font.render(errorMessage, True, errorColor)
        error_rect = error_surf.get_rect(center=(WIDTH // 2, 60))
        screen.blit(error_surf, error_rect)

    if currentPoly:
        status_text = f"Drawing polygon: {len(currentPoly)} points [ESC - cancel]"
        status_surf = font.render(status_text, True, statusColor)
        screen.blit(status_surf, (WIDTH // 2 - status_surf.get_width() // 2, HEIGHT - 30))

    draw_top_panel(screen)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()