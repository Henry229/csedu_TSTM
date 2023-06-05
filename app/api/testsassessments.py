import json
import math
import os
import random
import re
import string
import subprocess
from collections import namedtuple
from datetime import datetime, timedelta
from functools import wraps
from time import time

import pytz
from flask import jsonify, request, current_app, render_template
from flask_login import current_user, login_required
from sqlalchemy import desc, or_
from sqlalchemy.orm import load_only
from werkzeug.utils import secure_filename

from app.api import api
from app.decorators import permission_required_or_multiple
from app.models import Permission
from .. import db


@api.route('/stt/summaryreport')
@login_required
@permission_required_or_multiple(Permission.ITEM_EXEC, Permission.ASSESSMENT_READ)
def get_stt_summaryreport():
    sql_stmt = "with cte as ( " \
               "select t.*, " \
               " rank() over(partition by test_detail order by total desc) as rnk " \
               ",count(*) over(partition by test_detail) as cnt " \
               "from ( " \
               "select test_detail, " \
               "student_user_id, " \
               "max(percentile_score) filter (where subject = 'Mathematical Reasoning') as Math, " \
               "max(percentile_score) filter (where subject = 'Thinking Skills') as Thinking, " \
               "max(percentile_score) filter (where subject = 'Reading Skills') as Reading, " \
               "max(percentile_score) filter (where subject = 'Writing') as Writing, " \
               "(coalesce((max(percentile_score) filter (where subject = 'Mathematical Reasoning') * 0.25), 0) + " \
               "coalesce((max(percentile_score) filter (where subject = 'Thinking Skills') * 0.35), 0) + " \
               "coalesce((max(percentile_score) filter (where subject = 'Reading Skills') * 0.25), 0) + " \
               "coalesce((max(percentile_score) filter (where subject = 'Writing') * 0.15), 0)) as Total " \
               "from ( " \
               "select distinct test_detail(test_detail), student_user_id, " \
               "ae.id as assessment_enroll_id, " \
               "case when mw.id is not null and mw.candidate_mark_detail is not null then " \
               "(select sum(cast(mw.candidate_mark_detail->>code_name as integer)) * 100 / sum(cast(additional_info->>'max_score' as integer)) " \
               "from codebook where code_type = 'criteria' and parent_code = 1334 " \
               ") " \
               "else " \
               "	case when ae.total_score is null or ae.total_score=0 then 0 else round(((ae.score/ae.total_score) * 100)::numeric, 0) end " \
               "end as percentile_score " \
               ",(select code_name from codebook where id = ts.subject) as subject " \
               "from (select aa.test_detail, aa.name, bb.* from assessment aa join assessment_enroll bb on aa.id= bb.assessment_id where aa.test_type = 1334 " \
               "and aa.name like 'Selective No%' " \
               "and exists(select 1 from assessment_enroll where student_user_id = :student_user_id " \
               "and assessment_id = bb.assessment_id and testset_id = bb.testset_id) " \
               ") ae " \
               "join testset ts on ts.id = ae.testset_id " \
               "join marking m on m.assessment_enroll_id = ae.id " \
               "left join marking_writing mw on mw.marking_id = m.id " \
               ") tt " \
               "group by test_detail, student_user_id " \
               ") t " \
               ") " \
               "select test_detail, math, thinking, reading, writing, to_char(total, '999.99') as total, rnk, cnt " \
               "from cte " \
               "where student_user_id = :student_user_id " \
               "order by test_detail desc"
    cursor = db.session.execute(sql_stmt, {'student_user_id': current_user.id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return jsonify(rows)
