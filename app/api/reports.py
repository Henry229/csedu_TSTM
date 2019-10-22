import os

from PIL import Image, ImageDraw
from flask import current_app

from app.api import api
from app.decorators import permission_required
from app.models import Permission, refresh_mviews

graph_mapping = {
    "column_coords": {
        "ceiling": 558,
        "floor": 2433,
        "reading": {
            "centre": 818,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        },
        "writing": {
            "centre": 1635,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        },
        "grammar": {
            "centre": 1996,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": -1  # -1 for left, 1 for right
        },
        "spelling": {
            "centre": 2602,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        },
        "numeracy": {
            "centre": 3440,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        }
    },
    "score_ranges": {
        "Y3": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 50
        },
        "Y5": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 0
        },
        "Y7": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 0
        },
        "Y9": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 80,
            "lower_limit": 0
        }
    }
}


def draw_report(result):
    # Read base image
    if not os.path.exists(current_app.config['NAPLAN_RESULT_DIR']):
        os.makedirs(current_app.config['NAPLAN_RESULT_DIR'])
    base = Image.open('%s/../img/naplan-%s.png' % (current_app.config['NAPLAN_RESULT_DIR'], result["grade"]))
    base.load()
    img = Image.new("RGB", base.size, (255, 255, 255))
    img.paste(base, mask=base.split()[3])

    # Graph-Score ratio
    ceiling_score = graph_mapping["score_ranges"][result["grade"]]["ceiling_score"]
    floor_score = graph_mapping["score_ranges"][result["grade"]]["floor_score"]
    upper_limit = graph_mapping["score_ranges"][result["grade"]]["upper_limit"]
    lower_limit = graph_mapping["score_ranges"][result["grade"]]["lower_limit"]
    ratio = (graph_mapping["column_coords"]["floor"] - graph_mapping["column_coords"]["ceiling"]) / (
            ceiling_score - floor_score)

    # Draw overlays
    dctx = ImageDraw.Draw(img, 'RGBA')
    size = int(50 / 2)
    margin = 10

    def get_y(score):
        # Limit the score to keep it within the range
        if score >= upper_limit:
            score = upper_limit
        if score <= lower_limit:
            score = lower_limit
        # Calculate y
        if score > ceiling_score:
            y = graph_mapping["column_coords"]["ceiling"] - size - margin
        elif score < floor_score:
            y = graph_mapping["column_coords"]["floor"] + size + margin
        else:
            y = graph_mapping["column_coords"]["ceiling"] + (ceiling_score - score) * ratio
        return y

    for assessment, scores in result["assessments"].items():
        # 60% box
        x = graph_mapping["column_coords"][assessment]["centre"]
        o = graph_mapping["column_coords"][assessment]["offset"] * graph_mapping["column_coords"][assessment][
            "offset_direction"]
        y1 = get_y(scores["sixty"][0])
        y2 = get_y(scores["sixty"][1])
        dctx.rectangle((x - o, y1, x + o, y2), fill=(222, 238, 245, 125), outline="black")

        # Average score
        x = graph_mapping["column_coords"][assessment]["centre"] + o
        y = get_y(scores["average"])
        if o >= 0:  # on right side
            dctx.polygon([(x, y), (x + size + margin, y + size), (x + size + margin, y - size)], fill="black",
                         outline="black")
        else:  # on left side
            dctx.polygon([(x, y), (x - (size + margin), y - size), (x - (size + margin), y + size)], fill="black",
                         outline="black")

        # Student score
        x = graph_mapping["column_coords"][assessment]["centre"]
        y = get_y(scores["student"])
        dctx.ellipse((x - size, y - size, x + size, y + size), fill="black", outline="black")

    del dctx
    img.format = "PNG"
    # img.show()
    file_name = 'naplan-grade-%s_%s_%s.png' % (result["grade"], result["student_id"], result["assessment_GUID"])
    img.save('%s/%s' % (current_app.config['NAPLAN_RESULT_DIR'], file_name))
    return file_name

'''Refresh Mview for generating Report'''
@api.route('/gen_report/', methods=['POST'])
@permission_required(Permission.ASSESSMENT_MANAGE)
def gen_report():
    refresh_mviews()
    print('Finish refresh mviews')
    return 'True'