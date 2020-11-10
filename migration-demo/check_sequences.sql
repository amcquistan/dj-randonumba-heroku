
CREATE OR REPLACE FUNCTION check_sequence(seq TEXT, select_sql TEXT) RETURNS void
    LANGUAGE plpgsql
    PARALLEL UNSAFE
    AS $$
DECLARE
  max_pk INTEGER;
  next_seq_id INTEGER;
BEGIN
  EXECUTE select_sql INTO max_pk;
  SELECT nextval(seq) INTO next_seq_id;
  
  IF max_pk >= next_seq_id THEN 
    RAISE NOTICE '!!! Sequence (%) value (%) is less than or equal to max primary key value (%)', seq, next_seq_id, max_pk;
  ELSE
    RAISE NOTICE 'Sequence (%) OK!', seq;
  END IF;
END; $$;


SELECT check_sequence('public.auth_group_id_seq', 'SELECT MAX(id) FROM  public.auth_group');
SELECT check_sequence('public.auth_group_permissions_id_seq', 'SELECT MAX(id) FROM public.auth_group_permissions');
SELECT check_sequence('public.auth_permission_id_seq', 'SELECT MAX(id) FROM public.auth_permission');
SELECT check_sequence('public.auth_user_groups_id_seq', 'SELECT MAX(id) FROM public.auth_user_groups');
SELECT check_sequence('public.auth_user_id_seq', 'SELECT MAX(id) FROM public.auth_user');
SELECT check_sequence('public.auth_user_user_permissions_id_seq', 'SELECT MAX(id) FROM public.auth_user_user_permissions');
SELECT check_sequence('public.core_randonumba_id_seq', 'SELECT MAX(id) FROM public.core_randonumba');
SELECT check_sequence('public.django_admin_log_id_seq', 'SELECT MAX(id) FROM public.django_admin_log');
SELECT check_sequence('public.django_content_type_id_seq', 'SELECT MAX(id) FROM public.django_content_type');
SELECT check_sequence('public.django_migrations_id_seq', 'SELECT MAX(id) FROM public.django_migrations');

