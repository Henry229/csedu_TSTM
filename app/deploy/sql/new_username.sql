select u.id,
	u.username,
	s.student_id
from users u, student s
where u.id = s.user_id
and u.username not like s.student_id ;

update users
set username = ( select concat(u.username,' (',s.student_id,')') as new_username
               		from users u, student s
					where u.id = s.user_id
					and u.id = users.id)
where username not like '(' and username not like ')';

select u.id,
	u.username,
	s.student_id
from users u, student s
where u.id = s.user_id
and u.username not like s.student_id ;
