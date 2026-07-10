--
-- PostgreSQL database dump
--

\restrict HCzmKgakWodlrm6pgXofUC1b969HwkX5KsBCtGhutxUYzH0z7KKrnCChld63b6y

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: job_upload_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_upload_logs (
    log_id integer NOT NULL,
    job_id integer NOT NULL,
    status character varying(50),
    log_message text,
    update_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: job_upload_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_upload_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_upload_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_upload_logs_log_id_seq OWNED BY public.job_upload_logs.log_id;


--
-- Name: job_upload_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_upload_sessions (
    job_id integer NOT NULL,
    job_name character varying(255),
    job_path text,
    pic_job character varying(100),
    output_table character varying(255),
    upload_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    retry_count integer DEFAULT 0,
    original_upload_time timestamp with time zone,
    current_status character varying(50)
);


--
-- Name: job_upload_sessions_job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_upload_sessions_job_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_upload_sessions_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_upload_sessions_job_id_seq OWNED BY public.job_upload_sessions.job_id;


--
-- Name: staging_detected_tables; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_detected_tables (
    table_id integer NOT NULL,
    job_id integer NOT NULL,
    table_name character varying(255),
    table_category character varying(100)
);


--
-- Name: staging_detected_tables_table_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staging_detected_tables_table_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staging_detected_tables_table_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staging_detected_tables_table_id_seq OWNED BY public.staging_detected_tables.table_id;


--
-- Name: job_upload_logs log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_upload_logs ALTER COLUMN log_id SET DEFAULT nextval('public.job_upload_logs_log_id_seq'::regclass);


--
-- Name: job_upload_sessions job_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_upload_sessions ALTER COLUMN job_id SET DEFAULT nextval('public.job_upload_sessions_job_id_seq'::regclass);


--
-- Name: staging_detected_tables table_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_detected_tables ALTER COLUMN table_id SET DEFAULT nextval('public.staging_detected_tables_table_id_seq'::regclass);


--
-- Data for Name: job_upload_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_upload_logs (log_id, job_id, status, log_message, update_time) FROM stdin;
1382	51	Done	Categories updated successfully for 10 tables. Job completed.	2026-03-02 10:46:58.711083+07
1447	88	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:34:51.215+07
1450	88	Upload Failed	File Job tidak lengkap atau rusak (corrupt). Silakan unggah ulang file yang valid.	2026-05-11 13:34:54.539+07
1452	88	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:34:55.984+07
1453	88	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:34:57.131+07
1454	88	Upload Failed	File Job tidak lengkap atau rusak (corrupt). Silakan unggah ulang file yang valid.	2026-05-11 13:34:58.546+07
1455	88	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:34:59.634+07
1493	89	Done	Categories updated successfully for 1 tables. Job completed.	2026-05-11 14:23:15.726405+07
1448	88	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:34:51.244+07
1449	88	Upload Failed	File Job tidak lengkap atau rusak (corrupt). Silakan unggah ulang file yang valid.	2026-05-11 13:34:52.87+07
1451	88	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:34:55.82+07
1494	89	Upload Failed	LOREM IPSUM	2026-05-11 14:23:16.387+07
1456	88	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:35:13.81+07
1457	88	Upload Failed	File Job tidak lengkap atau rusak (corrupt). Silakan unggah ulang file yang valid.	2026-05-11 13:35:16.035+07
1458	88	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:35:17.101+07
1459	88	Upload Failed	File Job tidak lengkap atau rusak (corrupt). Silakan unggah ulang file yang valid.	2026-05-11 13:35:25.137+07
1460	88	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:35:26.371+07
1461	88	Need Confirmation	Berhasil mengekstrak lineage, tetapi ada data yang belum terpetakan. Silahkan tinjau skema!	2026-05-11 13:42:36.488+07
1462	88	Done	Categories updated successfully for 13 tables. Job completed.	2026-05-11 13:44:28.84039+07
1463	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:02.281+07
1464	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:02.345+07
1465	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:23.738+07
1466	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:23.88+07
1471	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:24.777+07
604	51	On Progress	Job berhasil ditambahkan! Sedang memproses lineage...	2026-02-23 15:00:31.382699+07
605	51	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-02-23 15:00:47.73+07
606	51	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-02-23 15:00:49.454+07
607	51	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-02-23 15:00:51.508+07
608	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.414+07
609	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.43+07
610	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.448+07
611	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.464+07
612	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.481+07
613	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.499+07
614	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.525+07
615	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.541+07
616	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.56+07
617	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.577+07
618	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.606+07
619	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.622+07
620	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.639+07
621	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.644+07
622	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.658+07
623	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.674+07
624	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.69+07
625	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.707+07
626	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.723+07
627	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.751+07
628	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.756+07
629	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.77+07
630	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.785+07
631	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.8+07
632	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.815+07
633	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.82+07
634	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.837+07
635	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.842+07
636	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.847+07
637	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.85+07
638	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.855+07
639	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.862+07
640	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.867+07
641	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.871+07
642	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.879+07
643	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.885+07
644	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.892+07
645	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.905+07
646	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.91+07
647	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.916+07
648	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.928+07
649	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.943+07
650	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.96+07
651	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.964+07
652	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.981+07
653	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:36.986+07
654	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37+07
655	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.013+07
656	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.016+07
657	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.023+07
658	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.028+07
659	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.034+07
660	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.038+07
661	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.044+07
662	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.048+07
663	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.054+07
664	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.062+07
665	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.067+07
666	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.071+07
667	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.077+07
668	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.081+07
669	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.088+07
1467	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:24.149+07
670	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.093+07
671	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.098+07
672	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.104+07
673	51	Upload Failed	Koneksi ke layanan AI terputus. Sistem gagal memproses permintaan.	2026-02-23 15:02:37.111+07
674	51	Need Confirmation	Berhasil mengekstrak lineage, tetapi ada data yang belum terpetakan. Silahkan tinjau skema!	2026-02-23 15:02:39.102+07
1468	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:24.603+07
1473	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:25.302+07
1469	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:24.683+07
1474	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:25.349+07
1470	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:24.764+07
1475	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:25.754+07
1472	88	Upload Failed	LOREM IPSUM	2026-05-11 13:45:24.858+07
1328	76	On Progress	Job berhasil ditambahkan! Sedang memproses lineage...	2026-03-01 19:46:52.233778+07
1476	89	On Progress	Job berhasil ditambahkan! Sedang memproses lineage...	2026-05-11 13:56:04.851298+07
1477	89	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:56:07.521+07
1564	106	On Progress	Job berhasil ditambahkan! Sedang memproses lineage...	2026-06-15 15:50:33.854551+07
1329	76	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-03-01 19:46:53.006+07
1330	76	Upload Failed	File Job tidak lengkap atau rusak (corrupt). Silakan unggah ulang file yang valid.	2026-03-01 19:46:53.873+07
1331	76	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-03-01 19:46:54.569+07
1332	76	Need Confirmation	Berhasil mengekstrak lineage, tetapi ada data yang belum terpetakan. Silahkan tinjau skema!	2026-03-01 19:47:07.076+07
1333	76	Done	Selesai: Seluruh data berhasil disimpan ke Database Utama	2026-03-01 19:47:07.769+07
1565	106	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-06-15 15:50:34.959+07
1566	106	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-06-15 15:50:35.973+07
1567	106	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-06-15 15:50:36.922+07
1568	106	On Progress	Berhasil mengenerate source table dari Job	2026-06-15 15:50:46.227+07
1569	106	Done	Selesai: Seluruh data berhasil disimpan ke Database Utama	2026-06-15 15:50:47.688+07
1478	89	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:56:07.525+07
1484	89	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-05-11 13:56:16.461+07
1485	89	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:56:17.992+07
1334	77	On Progress	Job berhasil ditambahkan! Sedang memproses lineage...	2026-03-01 19:49:36.522795+07
1445	88	On Progress	Job berhasil ditambahkan! Sedang memproses lineage...	2026-05-11 13:34:49.631392+07
1479	89	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:56:07.574+07
1480	89	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-05-11 13:56:09.804+07
1481	89	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:56:11.937+07
1482	89	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:56:13.571+07
1483	89	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-05-11 13:56:16.457+07
1486	89	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:56:18.006+07
1487	89	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:56:18.72+07
1488	89	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-05-11 13:56:20.431+07
1489	89	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:56:21.393+07
1490	89	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-05-11 13:56:23.441+07
1491	89	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-05-11 13:56:24.437+07
1335	77	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-03-01 19:49:37.241+07
1336	77	On Progress	Verifikasi file berhasil. Job file lengkap. Sedang cleaning dan mengganti contex paramaeter dengan value asli 	2026-03-01 19:49:38.783+07
1337	77	On Progress	Berhasil membersihkan query dan mengganti contex parameter	2026-03-01 19:49:39.941+07
1446	88	On Progress	Sedang Mengunduh: File Job berhasil ditemukan di FTP.	2026-05-11 13:34:51.166+07
1492	89	Need Confirmation	Berhasil mengekstrak lineage, tetapi ada data yang belum terpetakan. Silahkan tinjau skema!	2026-05-11 14:21:35.435+07
1338	77	Need Confirmation	Berhasil mengekstrak lineage, tetapi ada data yang belum terpetakan. Silahkan tinjau skema!	2026-03-01 19:51:43.93+07
1339	77	Done	Selesai: Seluruh data berhasil disimpan ke Database Utama	2026-03-01 19:51:45.436+07
\.


--
-- Data for Name: job_upload_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_upload_sessions (job_id, job_name, job_path, pic_job, output_table, upload_time, retry_count, original_upload_time, current_status) FROM stdin;
106	RDBMS_CDP_NEW_RMTOOLS_06PEER_ANALISIS_NEWRMT_DLY_H1	/RDBMS_CDP_NEW_RMTOOLS_06PEER_ANALISIS_NEWRMT_DLY_H1.zip	[10]	[597]	2026-06-15 15:50:33.843551+07	0	2026-06-15 15:50:33.843551+07	Done
88	RDBMS_CDP_NEW_RMTOOLS_DLY_H1	/RDBMS_CDP_NEW_RMTOOLS_DLY_H1_0.1.zip	[10]	[508, 509, 504, 510, 507, 436, 437, 438, 506, 440, 505, 501, 502, 503]	2026-05-11 13:34:49.607708+07	0	2026-05-11 13:34:49.607708+07	Upload Failed
89	DMT_WHL_DM_WALLET_SHARE_NEWRMT_DLY_H1	/DMT_WHL_DM_WALLET_SHARE_NEWRMT_DLY_H1_0.1.zip	[10]	[506]	2026-05-11 13:56:04.832481+07	0	2026-05-11 13:56:04.832481+07	Upload Failed
76	CDP_DMT_WHL_KOPRA_SUBSIDI_PRE_REQUISITE_DLY_H1	/CDP_DMT_WHL_KOPRA_SUBSIDI_PRE_REQUISITE_DLY_H1.zip	[7]	[418]	2026-03-01 19:46:52.223674+07	0	2026-03-01 19:46:52.223674+07	Done
77	CDP_DMT_WHL_EALCO_DLY_H0_TEST_WORKFLOW_BARU	/CDP_DMT_WHL_EALCO_DLY_H0.zip	[7]	[218, 239, 246, 243]	2026-03-01 19:49:36.511829+07	0	2026-03-01 19:49:36.511829+07	Done
51	CDP_DMT_WHL_EALCO_DLY_H0	/CDP_DMT_WHL_EALCO_DLY_H0.zip	[1, 9]	[218, 239, 246, 243]	2026-02-23 15:00:31.371541+07	0	2026-02-23 15:00:31.371541+07	Done
\.


--
-- Data for Name: staging_detected_tables; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.staging_detected_tables (table_id, job_id, table_name, table_category) FROM stdin;
1000	88	NEWDATAMART_STG.BASE_KREDIT_NEWRMT_STEP1	STAGING
1001	88	PROD_BM_BDA_PST.BMSTGCBS_CFMAST	SOURCE DATA
1002	88	PROD_BM_BDA_PST.BMSTGTF_CFNC_MAIN	SOURCE DATA
1003	88	PROD_BM_BDA_PST.BMSTGTF_KLN_CFNC_MAIN	SOURCE DATA
1004	88	PROD_BM_BDA_PST.BMSTGCNLS_RPT_ACCOUNT	SOURCE DATA
1005	88	PROD_BM_BDA_PST.BMSTGCNLS_RPT_CUSTOMER	SOURCE DATA
1006	88	NEWDATAMART_PST.DM_ACCPORT_MONTHLY	DATAMART
1007	88	NEWDATAMART_STG.BASE_KREDIT_NEWRMT_STEP0	STAGING
1008	88	NEWDATAMART_STG.BASE_GU_NEWRMT	STAGING
1009	88	PROD_BM_BDA_PST.WDMPORTAL_GROUP_USAHA	SOURCE DATA
1010	88	NEWDATAMART_PST.MASTER_WDMGU_BUCBRANCH	DATAMART
1011	88	NEWDATAMART_PST.RMT_BUC	DATAMART
1012	88	NEWDATAMART_PST.DPK	DATAMART
1013	88	NEWDATAMART_PST.F_DLY_DSR_UPDATE	DATAMART
1014	88	NEWDATAMART_PST.MASTER_CUST_BUCBRANCH_DLY	DATAMART
1015	88	NEWDATAMART_STG.BASE_DPK_NEWRMT_STEP1	STAGING
1016	88	NEWDATAMART_STG.BASE_DPK_NEWRMT	STAGING
1017	88	NEWDATAMART_PST.DM_CUSTOMER_NEWRMT_HIST	DATAMART
1018	88	NEWDATAMART_STG.BASE_DPK_NEWRMT_STEP2	STAGING
1019	88	NEWDATAMART_PST.DM_DPK_NEWRMT_HIST	DATAMART
1020	88	NEWDATAMART_STG.BASE_KREDIT_NEWRMT_STEP2	STAGING
1021	88	NEWDATAMART_STG.BASE_KREDIT_NCL_NEWRMT_STEP3	STAGING
1022	88	NEWDATAMART_STG.BASE_KREDIT_NCL_NEWRMT_STEP4	STAGING
1023	88	PRM.BRANCH	SOURCE DATA
1024	88	NEWDATAMART_STG.BASE_KREDIT_NEWRMT_STEP3	STAGING
1025	88	NEWDATAMART_PST.DM_KREDIT_NEWRMT_HIST	DATAMART
1026	88	NEWDATAMART_STG.BASE_DM_TREASURY_NEWRMT	STAGING
1027	88	PROD_BM_BDA_PST.BMSTGCBS_JHFXDT	SOURCE DATA
1028	88	NEWDATAMART_PST.MASTER_CUST_BUCBRANCH	DATAMART
1030	88	NEWDATAMART_PST.DM_CUSTOMER_NEWRMT_V2	DATAMART
1031	88	NEWDATAMART_STG.DM_TREASURY_NEWRMT	STAGING
1032	88	NEWDATAMART_PST.DM_TRANSACTION_V3	DATAMART
1033	88	NEWDATAMART_STG.BASE_REKENING_ANALISA_PELUANG_NEWRMT	STAGING
1034	88	NEWDATAMART_STG.BASE_ANALISA_PELUANG_NEWRMT_STEP1	STAGING
1035	88	NEWDATAMART_STG.DM_ANALISA_PELUANG_NEWRMT	STAGING
1037	88	NEWDATAMART_STG.BASE_GU_NEWRMT_STEP2	STAGING
1038	88	NEWDATAMART_STG.BASE_MSA_NEWRMT_STEP1	STAGING
1039	88	NEWDATAMART_STG.BASE_KREDIT_NCL_NEWRMT_STEP1	STAGING
1040	88	PRM.PAR_HIERARKI_BUC	SOURCE DATA
1041	88	NEWDATAMART_PST.MASTER_GU_NONGROUP_NEWRMT	DATAMART
1048	88	NEWDATAMART_STG.DM_TRANSACTION_NEWRMT	STAGING
1050	88	NEWDATAMART_PST.DM_ANALISA_PELUANG_NEWRMT_HIST	DATAMART
1051	88	NEWDATAMART_PST.DM_ANALISA_PELUANG_NEWRMT	DATAMART
1055	88	NEWDATAMART_PST.CIF_NORMALISASI	DATAMART
1056	88	NEWDATAMART_STG.DM_TRANSACTION_YTD_NEWRMT	STAGING
1057	88	PROD_BM_BDA_PST.BMSTGMSA_VIRTUAL_ACCOUNT_MASTER	SOURCE DATA
1058	88	PROD_BM_BDA_PST.BMSTGMSA_VIRTUAL_ACCOUNT_LIMIT_HIST	SOURCE DATA
1059	88	NEWDATAMART_PST.MSA_USERS	DATAMART
1060	88	PROD_BM_BDA_PST.BMSTGCBS_DDMAST	SOURCE DATA
1061	88	NEWDATAMART_STG.BASE_DHE_NEWRMT_STEP1	STAGING
1062	88	NEWDATAMART_PST.DM_BANK_SUMM_NEWRMT_HIST	DATAMART
1063	88	NEWDATAMART_PST.DM_TRANSACTION_NEWRMT_HIST	DATAMART
1064	88	NEWDATAMART_STG.DM_TRANSACTION_YOY_NEWRMT	STAGING
1065	88	NEWDATAMART_STG.FINAL_CUSTOMER_NEWRMT	STAGING
1066	88	NEWDATAMART_STG.FINAL_BUC_SEKTOR_CUSTOMER_NEWRMT	STAGING
1067	88	PROD_BM_BDA_PST.BMSTGCBS_CFYPIN	SOURCE DATA
1068	88	NEWDATAMART_PST.WALLET_SHARE_NEWRMT	DATAMART
1069	88	NEWDATAMART_STG.WALLET_SHARE_TAMBAHAN_NEWRMT	STAGING
1070	88	NEWDATAMART_STG.TAMBAHAN_ANPEL	STAGING
1071	88	PROD_BM_BDA_PST.BMSTGTF_STDS_CCL	SOURCE DATA
1072	88	PROD_BM_BDA_PST.BMSTGTF_STDS_COSH	SOURCE DATA
1073	88	PROD_BM_BDA_PST.BMSTGTF_STDS_CSL	SOURCE DATA
1074	88	NEWDATAMART_STG.BASE_KREDIT_NCL_NEWRMT_STEP2	STAGING
1075	88	PROD_BM_BDA_PST.BMSTGTF_IPLC_MASTER	SOURCE DATA
1076	88	PROD_BM_BDA_PST.BMSTGTF_BMTR_MASTER	SOURCE DATA
1077	88	PROD_BM_BDA_PST.BMSTGTF_EPLC_MASTER	SOURCE DATA
1078	88	PROD_BM_BDA_PST.BMSTGTF_ARFM_MASTER	SOURCE DATA
1079	88	PROD_BM_BDA_PST.BMSTGTF_IMCO_MASTER	SOURCE DATA
1080	88	PROD_BM_BDA_PST.BMSTGTF_EXCO_MASTER	SOURCE DATA
1081	88	PROD_BM_BDA_PST.BMSTGTF_PEFM_MASTER	SOURCE DATA
1082	88	PROD_BM_BDA_PST.BMSTGTF_SHGT_MASTER	SOURCE DATA
1083	88	PROD_BM_BDA_PST.BMSTGTF_BBFM_MASTER	SOURCE DATA
1084	88	PROD_BM_BDA_PST.BMSTGTF_KLN_EPLC_MASTER	SOURCE DATA
1085	88	PROD_BM_BDA_PST.BMSTGTF_KLN_BBFM_MASTER	SOURCE DATA
1086	88	NEWDATAMART_PST.TRADE_INTEREST	DATAMART
1087	88	NEWDATAMART_STG.DM_CUSTOMER_NEWRMT_V2	STAGING
1088	88	NEWDATAMART_PST.KREDIT	DATAMART
1090	88	NEWDATAMART_PST.DPK_GAB	DATAMART
1091	88	NEWDATAMART_PST.F_DLY_GSR	DATAMART
1036	88	ZZ_WBA_KINANTI.202311_UPLOAD_BANKCLEAN_NEW	STAGING
1042	88	BM_BDA_MDM_PST.SOURCESYSTEM	SOURCE DATA
1043	88	BM_BDA_MDM_PST.ADDRESS	SOURCE DATA
1044	88	BM_BDA_MDM_PST.CUSTOMER	SOURCE DATA
1045	88	BM_BDA_MDM_PST.IDENTIFIER	SOURCE DATA
1046	88	BM_BDA_KREDIT_PST.KREDIT_FINAL	SOURCE DATA
1047	88	BM_BDA_PST.BMSTGCBS_CFYPIN	SOURCE DATA
1049	88	ZZ_WBA.DETAIL_TRANSAKSI_KOPRA	DATAMART
1052	88	ZZ_WBA.DATAMART_UREG_USAK_KOPRA_FINAL	DATAMART
1053	88	ZZ_WBA.DETAIL_TRANSAKSI_KOPRA_FINAL	DATAMART
1054	88	ZZ_WBA.DETAIL_FBI_KOPRA	DATAMART
1089	88	ZZ_WBA_WIRA.JENIS_KREDIT_UPDATE_2025430	STAGING
175	51	NEWDATAMART_PST.DPK	DATAMART
176	51	NEWDATAMART_PST.MASTER_CUST_BUCBRANCH	DATAMART
177	51	PRM.PAR_HIERARKI_BUC	SOURCE DATA
162	51	WDMPORTAL.PIPELINE_FINAL	SOURCE DATA
163	51	WDMPORTAL.PIPELINE_LENDING_FINAL	SOURCE DATA
164	51	WDMPORTAL.PIPELINE_FINAL_DETAIL	SOURCE DATA
165	51	WDMPORTAL.PIPELINE	SOURCE DATA
166	51	WDMPORTAL.PIPELINE_DETAIL	SOURCE DATA
167	51	WDMPORTAL.PIPELINE_LENDING	SOURCE DATA
168	51	WDMPORTAL.SETTING_PARAMETER	SOURCE DATA
169	51	WDMPORTAL.SETTING_PARAMETER_DETAIL	SOURCE DATA
172	51	PROD_BM_BDA_STG.BMSTGCBS_CFMAST_TEMP	STAGING
174	51	ZZ_WBA_APRIN.CPA_2024	UNKNOWN
1092	88	PROD_BM_BDA_PST.BMSTGOPC_FXDH	SOURCE DATA
1093	88	PROD_BM_BDA_PST.BMSTGOPC_PUBS	SOURCE DATA
1094	88	PROD_BM_BDA_PST.BMSTGOPC_REVH	SOURCE DATA
1095	88	PROD_BM_BDA_PST.BMSTGOPC_VCUST	SOURCE DATA
1096	88	PROD_BM_BDA_PST.BMSTGOPC_CUST	SOURCE DATA
1097	89	NEWDATAMART_PST.DM_CUSTOMER_NEWRMT_HIST	DATAMART
1098	89	NEWDATAMART_PST.DPK	DATAMART
1099	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_CIF_BUC	STAGING
1100	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP0	STAGING
1101	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP0B	STAGING
1102	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP0A	STAGING
1104	89	NEWDATAMART_PST.CPGRP_CPA	DATAMART
1105	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP1A	STAGING
1106	89	NEWDATAMART_PST.KREDIT	DATAMART
1107	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP0B_KREDIT	STAGING
1108	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP0A_KREDIT	STAGING
1109	89	NEWDATAMART_STG.WALLET_SHARE_NEWRMT_STEP2C	STAGING
1110	89	NEWDATAMART_PST.WALLET_SHARE_NEWRMT	DATAMART
1103	89	ZZ_WBA.RMCC_FINANCIAL_HIGHLIGHT	DATAMART
170	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_FINAL	DATAMART
171	51	NEWDATAMART_PST.DEV_DPK_H0_DAENG	DATAMART
173	51	NEWDATAMART_STG.EALCO_DPK_COUNTERRATE_PIPELINE	STAGING
178	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_FINAL	DATAMART
179	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_LENDING_FINAL	DATAMART
180	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_FINAL_DETAIL	DATAMART
181	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_DETAIL	DATAMART
182	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_LENDING	DATAMART
183	51	NEWDATAMART_PST.WDMPORTAL_SETTING_PARAMETER	DATAMART
184	51	NEWDATAMART_PST.WDMPORTAL_SETTING_PARAM_DTL	DATAMART
185	51	NEWDATAMART_STG.WDMPORTAL_PIPELINE_FINAL_TEMP	STAGING
186	51	NEWDATAMART_STG.WDMPORTAL_PIPELINE_LENDING_FINAL_TEMP	STAGING
187	51	NEWDATAMART_STG.WDMPORTAL_PIPELINE_FINAL_DETAIL_TEMP	STAGING
188	51	NEWDATAMART_STG.WDMPORTAL_PIPELINE_TEMP	STAGING
189	51	NEWDATAMART_STG.WDMPORTAL_PIPELINE_DETAIL_TEMP	STAGING
190	51	NEWDATAMART_STG.WDMPORTAL_PIPELINE_LENDING_TEMP	STAGING
191	51	NEWDATAMART_STG.WDMPORTAL_SETTING_PARAMETER_TEMP	STAGING
192	51	NEWDATAMART_STG.WDMPORTAL_SETTING_PARAM_DTL_TEMP	STAGING
193	51	NEWDATAMART_PST.EALCO_DPK_PIPELINE_MONITORING	DATAMART
194	51	NEWDATAMART_STG.EALCO_DPK_PIPELINE_MONITORING	STAGING
195	51	NEWDATAMART_PST.EALCO_DPK_COUNTERRATE_PIPELINE	DATAMART
196	51	NEWDATAMART_STG.EALCO_KRD_PIPELINE_MONITORING	STAGING
197	51	NEWDATAMART_PST.WDMPORTAL_PIPELINE_LENDING_FINAL	DATAMART
198	51	NEWDATAMART_PST.KREDIT	DATAMART
199	51	NEWDATAMART_PST.KREDIT_H0	DATAMART
200	51	NEWDATAMART_PST.EALCO_KRD_PIPELINE_MONITORING	DATAMART
201	51	NEWDATAMART_STG.EALCO_KRD_NLTU_PIPELINE	STAGING
202	51	PRM.BMSTGCBS_LNPAR2	SOURCE DATA
203	51	NEWDATAMART_PST.EALCO_KRD_NLTU_PIPELINE	DATAMART
204	51	NEWDATAMART_STG.EALCO_DPK_PIPELINE_MONITORING	STAGING
205	51	NEWDATAMART_STG.EALCO_DPK_COUNTERRATE_PIPELINE	STAGING
206	51	NEWDATAMART_STG.EALCO_KRD_PIPELINE_MONITORING	STAGING
207	51	NEWDATAMART_STG.EALCO_KRD_NLTU_PIPELINE	STAGING
1029	88	ZZ_WBA_JUWITA.MAPPING_LOC_MASTERCUST	STAGING
\.


--
-- Name: job_upload_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.job_upload_logs_log_id_seq', 1569, true);


--
-- Name: job_upload_sessions_job_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.job_upload_sessions_job_id_seq', 106, true);


--
-- Name: staging_detected_tables_table_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.staging_detected_tables_table_id_seq', 1111, true);


--
-- Name: job_upload_logs job_upload_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_upload_logs
    ADD CONSTRAINT job_upload_logs_pkey PRIMARY KEY (log_id);


--
-- Name: job_upload_sessions job_upload_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_upload_sessions
    ADD CONSTRAINT job_upload_sessions_pkey PRIMARY KEY (job_id);


--
-- Name: staging_detected_tables staging_detected_tables_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_detected_tables
    ADD CONSTRAINT staging_detected_tables_pkey PRIMARY KEY (table_id);


--
-- Name: idx_job_sessions_current_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_job_sessions_current_status ON public.job_upload_sessions USING btree (current_status);


--
-- Name: job_upload_logs fk_logs_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_upload_logs
    ADD CONSTRAINT fk_logs_job FOREIGN KEY (job_id) REFERENCES public.job_upload_sessions(job_id) ON DELETE CASCADE;


--
-- Name: staging_detected_tables fk_staging_job; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_detected_tables
    ADD CONSTRAINT fk_staging_job FOREIGN KEY (job_id) REFERENCES public.job_upload_sessions(job_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict HCzmKgakWodlrm6pgXofUC1b969HwkX5KsBCtGhutxUYzH0z7KKrnCChld63b6y

