
CREATE OR REPLACE FUNCTION alter_sequence(seq TEXT, select_sql TEXT) RETURNS void
    LANGUAGE plpgsql
    PARALLEL UNSAFE
    AS $$
DECLARE
  max_pk INTEGER;
  new_seq_id INTEGER;
  seq_id_offset INTEGER := 9000;
BEGIN
  EXECUTE select_sql INTO max_pk;
  new_seq_id = max_pk + seq_id_offset;
  RAISE NOTICE 'Max PK=% and new Seq Val=% from SQL=%', max_pk, new_seq_id, select_sql;

  PERFORM setval(seq, new_seq_id);
END; $$;


BEGIN;

SELECT alter_sequence('public.auth_group_id_seq', 'SELECT MAX(id) FROM  public.auth_group');
SELECT alter_sequence('public.auth_group_permissions_id_seq', 'SELECT MAX(id) FROM public.auth_group_permissions');
SELECT alter_sequence('public.auth_permission_id_seq', 'SELECT MAX(id) FROM public.auth_permission');
SELECT alter_sequence('public.auth_user_groups_id_seq', 'SELECT MAX(id) FROM public.auth_user_groups');
SELECT alter_sequence('public.auth_user_id_seq', 'SELECT MAX(id) FROM public.auth_user');
SELECT alter_sequence('public.auth_user_user_permissions_id_seq', 'SELECT MAX(id) FROM public.auth_user_user_permissions');
SELECT alter_sequence('public.core_randonumba_id_seq', 'SELECT MAX(id) FROM public.core_randonumba');
SELECT alter_sequence('public.django_admin_log_id_seq', 'SELECT MAX(id) FROM public.django_admin_log');
SELECT alter_sequence('public.django_content_type_id_seq', 'SELECT MAX(id) FROM public.django_content_type');
SELECT alter_sequence('public.django_migrations_id_seq', 'SELECT MAX(id) FROM public.django_migrations');

COMMIT;

