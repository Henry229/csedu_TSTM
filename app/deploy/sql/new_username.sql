select u.id,
	u.username,
	s.student_id
from users u, student s
where u.id = s.user_id
and (username like '%(%' and username like '%)%');

update users
set username = ( select concat(u.username,' (',s.student_id,')') as new_username
               		from users u, student s
					where u.id = s.user_id
					and u.id = users.id)
where not (username like '%(%' and username like '%)');

select u.id,
	u.username,
	s.student_id
from users u, student s
where u.id = s.user_id ;
and (username like '%(%' and username like '%)%');
