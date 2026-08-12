--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: application_roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.application_roles (role_id, role_name) FROM stdin;
1	admin
2	medecin
3	nurse
4	secretaire
5	laborantin
6	Psychologist
7	SpiritualCounsellor
8	ToxicoManager
9	Assistant
\.


--
-- Name: application_roles_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.application_roles_role_id_seq', 57, true);


--
-- PostgreSQL database dump complete
--

