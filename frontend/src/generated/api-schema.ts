export interface paths {
    "/api/activity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Activity
         * @description Hareket akisi.
         *
         *     `category` emek haritasi kategorilerinden biri (read/task/focus/routine/
         *     study/media) ya da "system" (haritada sayilmayan worker kayitlari).
         *     `q` baslik/aciklama/verb icinde arar; `offset` ile "daha fazla yukle"
         *     yapilir. Ayni kayit iki kez gelmesin diye sira (occurred_at, id) sabittir.
         */
        get: operations["activity_api_activity_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/activity/day": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Activity Day
         * @description Tek gunun dokumu -- emek haritasi karesinin hedefi.
         */
        get: operations["activity_day_api_activity_day_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/activity/heatmap": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Activity Heatmap
         * @description Gunluk emek haritasi -- sadece insan eliyle yapilan isler sayilir.
         */
        get: operations["activity_heatmap_api_activity_heatmap_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/applications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Applications List
         * @description Başvurular çalışma alanı: YALNIZCA gerçek başvuru kayıtları.
         *
         *     Keşfedilmiş ilanlar buraya hiçbir koşulda girmez (Faz 4.1).
         */
        get: operations["applications_list_api_applications_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/applications/funnel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Applications Funnel */
        get: operations["applications_funnel_api_applications_funnel_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/applications/rejection-reasons": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Rejection Reasons */
        get: operations["rejection_reasons_api_applications_rejection_reasons_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/applications/{item_id}/transition": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Application Transition
         * @description Basvuru hatti gecisi (yalnizca gercek basvuru kayitlari).
         */
        post: operations["application_transition_api_applications__item_id__transition_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/github": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Github Credentials */
        post: operations["github_credentials_api_auth_github_post"];
        /**
         * Github Disconnect
         * @description GitHub token'ini siler: panel ve commit akislari aninda anonim limite doner.
         */
        delete: operations["github_disconnect_api_auth_github_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/github/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Github Status */
        get: operations["github_status_api_auth_github_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/google": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Disconnect
         * @description Google Drive token'ini siler; yeni senkron icin yeniden baglanmak gerekir.
         */
        delete: operations["disconnect_api_auth_google_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/google/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Callback */
        get: operations["callback_api_auth_google_callback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/google/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Auth Start */
        get: operations["auth_start_api_auth_google_start_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/google/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Status */
        get: operations["status_api_auth_google_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Backup */
        post: operations["run_backup_api_backup_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backup/inspect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Inspect Backup
         * @description Import oncesi preflight: yedegi hicbir sey yazmadan inceler.
         *
         *     Format versiyonu, tablo/satir sayilari, bilinmeyen tablolar, eksik
         *     bolumler, secret setting satirlari ve manifest butunlugu raporlanir.
         *     Kullanici raporu gorup onayladiktan sonra `/backup/restore` cagrilir.
         */
        post: operations["inspect_backup_api_backup_inspect_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backup/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Restore Backup
         * @description Birleştirerek içe aktar (merge import) -- tam geri donus DEGILDIR.
         *
         *     Idempotent + cakismasiz: `ON CONFLICT DO NOTHING`, var olan kayitlara
         *     dokunulmaz, eksikler eklenir. Ayni yedek defalarca yuklenebilir.
         *     Gercek felaket kurtarmasi app disindadir: `make disaster-restore`.
         */
        post: operations["restore_backup_api_backup_restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/backup/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Backup Status
         * @description Son yedek, Drive yukleme durumu ve yedek kapsami -- tek bakisla.
         */
        get: operations["backup_status_api_backup_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Bookmarks */
        get: operations["list_bookmarks_api_bookmarks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/bulk-action": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bulk Action Bookmarks */
        post: operations["bulk_action_bookmarks_api_bookmarks_bulk_action_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export Bookmarks
         * @description Netscape Bookmark HTML formatinda kutuphane dosyasini indirir.
         */
        get: operations["export_bookmarks_api_bookmarks_export_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Bookmarks
         * @description Netscape HTML veya Pocket JSON formatinda yer imi yukler.
         */
        post: operations["import_bookmarks_api_bookmarks_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bookmark Stats */
        get: operations["bookmark_stats_api_bookmarks_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Bookmark */
        get: operations["get_bookmark_api_bookmarks__bookmark_id__get"];
        put?: never;
        post?: never;
        /** Delete Bookmark */
        delete: operations["delete_bookmark_api_bookmarks__bookmark_id__delete"];
        options?: never;
        head?: never;
        /** Update Bookmark */
        patch: operations["update_bookmark_api_bookmarks__bookmark_id__patch"];
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/collection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Move Bookmark
         * @description Surukle-birak buraya duser: tek UPDATE, link ve event kopmaz.
         */
        patch: operations["move_bookmark_api_bookmarks__bookmark_id__collection_patch"];
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/convert-to-task": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Convert Bookmark To Task */
        post: operations["convert_bookmark_to_task_api_bookmarks__bookmark_id__convert_to_task_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/create-note": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Note From Bookmark */
        post: operations["create_note_from_bookmark_api_bookmarks__bookmark_id__create_note_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/enrich": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Enrich Bookmark */
        post: operations["enrich_bookmark_api_bookmarks__bookmark_id__enrich_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/fulltext": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Bookmark Fulltext
         * @description Makalenin tam metni, temizlenmis HTML'i ve vurgulari.
         */
        get: operations["get_bookmark_fulltext_api_bookmarks__bookmark_id__fulltext_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/highlights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Bookmark Highlights */
        get: operations["list_bookmark_highlights_api_bookmarks__bookmark_id__highlights_get"];
        put?: never;
        /** Add Bookmark Highlight */
        post: operations["add_bookmark_highlight_api_bookmarks__bookmark_id__highlights_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/highlights/{highlight_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Bookmark Highlight */
        delete: operations["delete_bookmark_highlight_api_bookmarks__bookmark_id__highlights__highlight_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/highlights/{highlight_id}/convert-to-flashcard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Convert Highlight To Flashcard */
        post: operations["convert_highlight_to_flashcard_api_bookmarks__bookmark_id__highlights__highlight_id__convert_to_flashcard_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/bookmarks/{bookmark_id}/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Update Bookmark Progress
         * @description Okuma yuzdesini gunceller. Yuzde >= 90 ise otomatik okundu yapilir.
         */
        patch: operations["update_bookmark_progress_api_bookmarks__bookmark_id__progress_patch"];
        trace?: never;
    };
    "/api/calendar/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Calendar Events */
        get: operations["calendar_events_api_calendar_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/calendar/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sync Calendar */
        post: operations["sync_calendar_api_calendar_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/capture": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Capture
         * @description Extension ve quick capture giris noktasi. Idempotent (client_uuid).
         *
         *     Ayni URL ikinci kez gelirse 409 DEGIL, 201 + duplicate=true doner --
         *     extension popup'i "zaten kayitli, tasimak ister misin?" gosterir.
         */
        post: operations["capture_api_capture_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/connections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Career Connections */
        get: operations["career_connections_api_career_connections_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/connections/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Career Connections */
        post: operations["import_career_connections_api_career_connections_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/cover-letter-review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cover Letter Review */
        post: operations["cover_letter_review_api_career_cover_letter_review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/stories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Career Stories */
        get: operations["career_stories_api_career_stories_get"];
        put?: never;
        /** Create Career Story */
        post: operations["create_career_story_api_career_stories_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/stories/{story_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Archive Career Story */
        delete: operations["archive_career_story_api_career_stories__story_id__delete"];
        options?: never;
        head?: never;
        /** Patch Career Story */
        patch: operations["patch_career_story_api_career_stories__story_id__patch"];
        trace?: never;
    };
    "/api/courses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Courses */
        get: operations["courses_api_courses_get"];
        put?: never;
        /** Add Course */
        post: operations["add_course_api_courses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/courses/{course_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Course */
        delete: operations["delete_course_api_courses__course_id__delete"];
        options?: never;
        head?: never;
        /** Patch Course */
        patch: operations["patch_course_api_courses__course_id__patch"];
        trace?: never;
    };
    "/api/deadlines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Deadlines
         * @description Son tarihli kayitlar -- kayitli modul saglayicilarindan (kural 16).
         */
        get: operations["deadlines_api_deadlines_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Documents */
        get: operations["documents_api_documents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sync */
        post: operations["sync_api_documents_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents/upload": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload Document */
        post: operations["upload_document_api_documents_upload_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents/usages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Document Usages
         * @description Her belge için kullanıldığı fırsat özetleri (cv/requirement bağları).
         */
        get: operations["document_usages_api_documents_usages_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Document */
        delete: operations["delete_document_api_documents__id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents/{id}/file": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Document File */
        get: operations["get_document_file_api_documents__id__file_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/documents/{id}/open": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Open Doc */
        get: operations["open_doc_api_documents__id__open_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/entities/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Entity Detail */
        get: operations["entity_detail_api_entities__entity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/entities/{entity_id}/backlinks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Entity Backlinks
         * @description Bu kayda [[...]] ile baglanan kayitlar.
         */
        get: operations["entity_backlinks_api_entities__entity_id__backlinks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/entities/{entity_id}/related": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Related
         * @description Bagli kayitlar: iliski + yon (outgoing/incoming) + karsi entity ozeti.
         */
        get: operations["related_api_entities__entity_id__related_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/expenses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Expenses */
        get: operations["expenses_api_expenses_get"];
        put?: never;
        /** Add Expense */
        post: operations["add_expense_api_expenses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/expenses/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Expense */
        delete: operations["delete_expense_api_expenses__item_id__delete"];
        options?: never;
        head?: never;
        /** Patch Expense */
        patch: operations["patch_expense_api_expenses__item_id__patch"];
        trace?: never;
    };
    "/api/export/bookmarks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Bookmarks */
        get: operations["export_bookmarks_api_export_bookmarks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/export/csv": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Csv */
        get: operations["export_csv_api_export_csv_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/export/ics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Ics */
        get: operations["export_ics_api_export_ics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/export/json": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Json */
        get: operations["export_json_api_export_json_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/export/markdown": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Markdown */
        get: operations["export_markdown_api_export_markdown_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/export/opml": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Opml */
        get: operations["export_opml_api_export_opml_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/finance/overview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Overview
         * @description Bir ayin gelir/gider/net tablosu -- sayfa basligi tek cagriyla dolar.
         */
        get: operations["overview_api_finance_overview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/finance/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Summary
         * @description Son `months` ayin gelir/gider toplamlari -- sayfa grafigi serisi.
         */
        get: operations["summary_api_finance_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/cards/{card_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Card */
        delete: operations["delete_card_api_flashcard_cards__card_id__delete"];
        options?: never;
        head?: never;
        /** Patch Card */
        patch: operations["patch_card_api_flashcard_cards__card_id__patch"];
        trace?: never;
    };
    "/api/flashcard/cards/{card_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review */
        post: operations["review_api_flashcard_cards__card_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/cram/missed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Cram Missed
         * @description Desteler genelinde en cok unutulan kartlar (varsayilan 30) -- cram kuyrugu.
         */
        get: operations["cram_missed_api_flashcard_cram_missed_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/decks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Decks
         * @description Desteler. `linked_to` verilirse yalnizca o kayda bagli olanlar doner
         *     (not/dokuman -> deste bagi "studies"/"generated_from").
         */
        get: operations["decks_api_flashcard_decks_get"];
        put?: never;
        /** Add Deck */
        post: operations["add_deck_api_flashcard_decks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/decks/{deck_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Deck */
        delete: operations["delete_deck_api_flashcard_decks__deck_id__delete"];
        options?: never;
        head?: never;
        /** Patch Deck */
        patch: operations["patch_deck_api_flashcard_decks__deck_id__patch"];
        trace?: never;
    };
    "/api/flashcard/decks/{deck_id}/cards": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Cards
         * @description ?due=1: tekrar sirasi (once vadesi gelen, sonra yeni; her biri 40 kart).
         *
         *     `only_lapses=1` zayif noktalari suzer (lapses >= 1), `q` on/arka yuzde arar.
         */
        get: operations["cards_api_flashcard_decks__deck_id__cards_get"];
        put?: never;
        /** Add Card */
        post: operations["add_card_api_flashcard_decks__deck_id__cards_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Cards
         * @description Anki .apkg / .csv / .txt ic aktarim. `deck` = hedef destek adi (opsiyonel).
         */
        post: operations["import_cards_api_flashcard_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/graph": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Knowledge Graph
         * @description Bilgi grafi: dugum = entity, kenar = link. focus verilirse o kaydin cevresi.
         */
        get: operations["knowledge_graph_api_graph_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incomes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Incomes */
        get: operations["incomes_api_incomes_get"];
        put?: never;
        /** Add Income */
        post: operations["add_income_api_incomes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/incomes/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Income */
        delete: operations["delete_income_api_incomes__item_id__delete"];
        options?: never;
        head?: never;
        /** Patch Income */
        patch: operations["patch_income_api_incomes__item_id__patch"];
        trace?: never;
    };
    "/api/interviews/{interview_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Interview */
        delete: operations["delete_interview_api_interviews__interview_id__delete"];
        options?: never;
        head?: never;
        /** Patch Interview */
        patch: operations["patch_interview_api_interviews__interview_id__patch"];
        trace?: never;
    };
    "/api/learning/resources/{resource_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Resource
         * @description Tek kaynak (deep-link) + `last_opened_at` damgasi.
         */
        get: operations["get_resource_api_learning_resources__resource_id__get"];
        put?: never;
        post?: never;
        /** Delete Resource */
        delete: operations["delete_resource_api_learning_resources__resource_id__delete"];
        options?: never;
        head?: never;
        /** Patch Resource */
        patch: operations["patch_resource_api_learning_resources__resource_id__patch"];
        trace?: never;
    };
    "/api/links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Link */
        post: operations["create_link_api_links_post"];
        /** Delete Link */
        delete: operations["delete_link_api_links_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Media */
        get: operations["list_media_api_media_get"];
        put?: never;
        /** Create Media */
        post: operations["create_media_api_media_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/artwork/proxy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Media Artwork Proxy
         * @description Uzak saglayici gorselini yerel onbellege alip sunar (local-only gizlilik).
         */
        get: operations["media_artwork_proxy_api_media_artwork_proxy_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/artwork/prune": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Media Artwork Prune */
        post: operations["media_artwork_prune_api_media_artwork_prune_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/artwork/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Artwork Stats */
        get: operations["media_artwork_stats_api_media_artwork_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/assets/{asset_name}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Asset */
        get: operations["media_asset_api_media_assets__asset_name__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/collections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Collections */
        get: operations["collections_api_media_collections_get"];
        put?: never;
        /** Create Collection */
        post: operations["create_collection_api_media_collections_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/collections/{collection_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Collection Detail */
        get: operations["collection_detail_api_media_collections__collection_id__get"];
        put?: never;
        post?: never;
        /** Delete Collection */
        delete: operations["delete_collection_api_media_collections__collection_id__delete"];
        options?: never;
        head?: never;
        /** Update Collection */
        patch: operations["update_collection_api_media_collections__collection_id__patch"];
        trace?: never;
    };
    "/api/media/collections/{collection_id}/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Collection Item */
        post: operations["add_collection_item_api_media_collections__collection_id__items__item_id__post"];
        /** Remove Collection Item */
        delete: operations["remove_collection_item_api_media_collections__collection_id__items__item_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Media Dashboard
         * @description Istatistik ekraninin tek istegi (ozet + devam + yaklasan + son tuketimler).
         */
        get: operations["media_dashboard_api_media_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/providers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Providers */
        get: operations["media_providers_api_media_providers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/search/global": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search All Metadata */
        get: operations["search_all_metadata_api_media_search_global_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Stats */
        get: operations["media_stats_api_media_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Queue Media Sync */
        post: operations["queue_media_sync_api_media_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/upcoming": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Upcoming */
        get: operations["media_upcoming_api_media_upcoming_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Detail */
        get: operations["media_detail_api_media__item_id__get"];
        put?: never;
        post?: never;
        /** Trash Media */
        delete: operations["trash_media_api_media__item_id__delete"];
        options?: never;
        head?: never;
        /** Update Media */
        patch: operations["update_media_api_media__item_id__patch"];
        trace?: never;
    };
    "/api/media/{item_id}/consumptions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Consumptions */
        get: operations["media_consumptions_api_media__item_id__consumptions_get"];
        put?: never;
        /** Consume Media */
        post: operations["consume_media_api_media__item_id__consumptions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/{item_id}/cycles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Cycles */
        get: operations["media_cycles_api_media__item_id__cycles_get"];
        put?: never;
        /** Start Media Cycle */
        post: operations["start_media_cycle_api_media__item_id__cycles_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/{item_id}/permanent": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Permanent Delete Media */
        delete: operations["permanent_delete_media_api_media__item_id__permanent_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/media/{item_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore Media */
        post: operations["restore_media_api_media__item_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/milestones/{milestone_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Milestone */
        delete: operations["delete_milestone_api_milestones__milestone_id__delete"];
        options?: never;
        head?: never;
        /** Patch Milestone */
        patch: operations["patch_milestone_api_milestones__milestone_id__patch"];
        trace?: never;
    };
    "/api/news/github-trending": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Github Trending */
        get: operations["github_trending_api_news_github_trending_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/hacker-news": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Hacker News */
        get: operations["hacker_news_api_news_hacker_news_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/reddit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Reddit News
         * @description Bugun panelindeki reddit akisi -- tech/CS subredditleri.
         *
         *     Sunucudan cekilir: reddit tarayiciya 403 doner (bkz. news.py).
         *     Kaynak listesi "news.subreddits" ayarindan; yoksa varsayilanlar.
         */
        get: operations["reddit_news_api_news_reddit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/note-folders": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Note Folders */
        get: operations["list_note_folders_api_note_folders_get"];
        put?: never;
        /** Create Note Folder */
        post: operations["create_note_folder_api_note_folders_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/note-folders/{folder_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Note Folder */
        delete: operations["delete_note_folder_api_note_folders__folder_id__delete"];
        options?: never;
        head?: never;
        /** Patch Note Folder */
        patch: operations["patch_note_folder_api_note_folders__folder_id__patch"];
        trace?: never;
    };
    "/api/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Notes */
        get: operations["list_notes_api_notes_get"];
        put?: never;
        /** Create Note */
        post: operations["create_note_api_notes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notes/{note_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Note */
        get: operations["get_note_api_notes__note_id__get"];
        put?: never;
        post?: never;
        /** Delete Note */
        delete: operations["delete_note_api_notes__note_id__delete"];
        options?: never;
        head?: never;
        /** Patch Note */
        patch: operations["patch_note_api_notes__note_id__patch"];
        trace?: never;
    };
    "/api/notes/{note_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Note */
        post: operations["archive_note_api_notes__note_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notes/{note_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload Attachment */
        post: operations["upload_attachment_api_notes__note_id__attachments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notes/{note_id}/attachments/{attachment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Attachment */
        get: operations["get_attachment_api_notes__note_id__attachments__attachment_id__get"];
        put?: never;
        post?: never;
        /** Remove Attachment */
        delete: operations["remove_attachment_api_notes__note_id__attachments__attachment_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Notifications */
        get: operations["notifications_api_notifications_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/dismiss-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss All Notifications */
        post: operations["dismiss_all_notifications_api_notifications_dismiss_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/read-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Read All Notifications */
        post: operations["read_all_notifications_api_notifications_read_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/{notification_id}/dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss Notification */
        post: operations["dismiss_notification_api_notifications__notification_id__dismiss_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/{notification_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Read Notification */
        post: operations["read_notification_api_notifications__notification_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Opportunities */
        get: operations["opportunities_api_opportunities_get"];
        put?: never;
        /** Create */
        post: operations["create_api_opportunities_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/browse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Opportunity Browse */
        get: operations["opportunity_browse_api_opportunities_browse_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/followups": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Followups */
        get: operations["followups_api_opportunities_followups_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/lifecycle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Opportunity Lifecycle
         * @description Kesif, basvuru ve duyuru durum makineleri.
         *
         *     Frontend durum seceneklerini ve izinli gecisleri BURADAN okur; elle
         *     kopyalanmis statu listesi tutmaz (AGENTS.md kural 13).
         */
        get: operations["opportunity_lifecycle_api_opportunities_lifecycle_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/prune": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Prune Opportunities
         * @description Onaylanmis silme: yalnizca sahipsiz ham ilanlar gider, event uretilir.
         */
        post: operations["prune_opportunities_api_opportunities_prune_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/prune/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Prune Preview
         * @description Dry-run: ne silinir, ne korunur, tahmini ne kadar yer bosalir.
         *
         *     Silme yalnizca bu onizlemeden alinan `confirm_token` ile yapilir; boylece
         *     tek tikla geri alinamaz veri kaybi olmaz (Faz 2.3).
         */
        get: operations["prune_preview_api_opportunities_prune_preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/silence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Silent Applications */
        get: operations["silent_applications_api_opportunities_silence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Opportunity Detail */
        get: operations["opportunity_detail_api_opportunities__item_id__get"];
        put?: never;
        post?: never;
        /** Delete */
        delete: operations["delete_api_opportunities__item_id__delete"];
        options?: never;
        head?: never;
        /** Patch */
        patch: operations["patch_api_opportunities__item_id__patch"];
        trace?: never;
    };
    "/api/opportunities/{item_id}/application": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Application Detail */
        get: operations["application_detail_api_opportunities__item_id__application_get"];
        /** Application Update */
        put: operations["application_update_api_opportunities__item_id__application_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply
         * @description Basvur: basvuru kaydi 'applied' olur, snapshot + CV kunyesi saklanir.
         */
        post: operations["apply_api_opportunities__item_id__apply_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/connections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Connections For Opportunity */
        get: operations["connections_for_opportunity_api_opportunities__item_id__connections_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/evaluation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Save Evaluation */
        put: operations["save_evaluation_api_opportunities__item_id__evaluation_put"];
        /** Generate Evaluation */
        post: operations["generate_evaluation_api_opportunities__item_id__evaluation_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** History */
        get: operations["history_api_opportunities__item_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/interviews": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Interviews */
        get: operations["interviews_api_opportunities__item_id__interviews_get"];
        put?: never;
        /** Add Interview */
        post: operations["add_interview_api_opportunities__item_id__interviews_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Opportunity Notes */
        get: operations["opportunity_notes_api_opportunities__item_id__notes_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/reply-analysis": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reply Analysis */
        post: operations["reply_analysis_api_opportunities__item_id__reply_analysis_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/requirements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Requirements */
        get: operations["requirements_api_opportunities__item_id__requirements_get"];
        put?: never;
        /** Requirement */
        post: operations["requirement_api_opportunities__item_id__requirements_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/research-note": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Get Or Create Research Note */
        post: operations["get_or_create_research_note_api_opportunities__item_id__research_note_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore */
        post: operations["restore_api_opportunities__item_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/salary-consistency": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Opportunity Salary Consistency */
        get: operations["opportunity_salary_consistency_api_opportunities__item_id__salary_consistency_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Application Timeline
         * @description Birlesik basvuru zaman cizelgesi (kesif + basvuru + gorusme + not + gorev).
         */
        get: operations["application_timeline_api_opportunities__item_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/todos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Opportunity Todos */
        get: operations["opportunity_todos_api_opportunities__item_id__todos_get"];
        put?: never;
        /** Add Opportunity Todo */
        post: operations["add_opportunity_todo_api_opportunities__item_id__todos_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/transition": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Transition
         * @description Kesif/duyuru durum gecisi: gecmis + event yazar; tur kumesine uyar.
         */
        post: operations["transition_api_opportunities__item_id__transition_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{item_id}/trash": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Trash */
        post: operations["trash_api_opportunities__item_id__trash_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Plan */
        get: operations["get_plan_api_plan_get"];
        put?: never;
        /** Create Slot */
        post: operations["create_slot_api_plan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/plan/carry-over": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Carry Over
         * @description Bir gunun acik todo slotlarini hedef gune tasir (Faz 33) -- tek
         *     transaction, atomik; tamamlanmis/dropped gorev slotlari tasinmaz.
         */
        post: operations["carry_over_api_plan_carry_over_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/plan/{slot_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Slot */
        delete: operations["delete_slot_api_plan__slot_id__delete"];
        options?: never;
        head?: never;
        /** Update Slot */
        patch: operations["update_slot_api_plan__slot_id__patch"];
        trace?: never;
    };
    "/api/plan/{slot_id}/push": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Push Plan */
        post: operations["push_plan_api_plan__slot_id__push_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Manual
         * @description Sayac calistirilmadan yapilan isi gecmise isler.
         */
        post: operations["add_manual_api_pomodoro_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/active": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Active */
        get: operations["active_api_pomodoro_active_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/contexts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Contexts
         * @description Odak seansina baglam olabilecek kayitlar (gorev, konu, kaynak...).
         */
        get: operations["contexts_api_pomodoro_contexts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sessions */
        get: operations["sessions_api_pomodoro_sessions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start */
        post: operations["start_api_pomodoro_start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stats */
        get: operations["stats_api_pomodoro_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/{pomo_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete */
        delete: operations["delete_api_pomodoro__pomo_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/{pomo_id}/pause": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pause */
        post: operations["pause_api_pomodoro__pomo_id__pause_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/{pomo_id}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resume */
        post: operations["resume_api_pomodoro__pomo_id__resume_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/pomodoro/{pomo_id}/stop": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Stop */
        post: operations["stop_api_pomodoro__pomo_id__stop_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Projects */
        get: operations["projects_api_projects_get"];
        put?: never;
        /** Add Project */
        post: operations["add_project_api_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Delete Project
         * @description Projeyi siler.
         *
         *     Kilometre taslari ve link'ler cascade ile gider; PROJEYE BAGLI GOREVLER
         *     KALIR -- is bitmedigi icin projenin kapanmasi gorevleri yok etmemeli.
         */
        delete: operations["delete_project_api_projects__project_id__delete"];
        options?: never;
        head?: never;
        /** Patch Project */
        patch: operations["patch_project_api_projects__project_id__patch"];
        trace?: never;
    };
    "/api/projects/{project_id}/github": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Project Github
         * @description Projeye bagli deponun paneli: ozet, acik issue/PR, son commit'ler.
         */
        get: operations["project_github_api_projects__project_id__github_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}/github/issues": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Issue To Todo
         * @description GitHub issue'sunu gorev yapar ve projeye baglar.
         *
         *     Ayni issue ikinci kez gonderilirse yeni gorev acilmaz -- mevcut gorev
         *     doner. Boylece "gorev olustur" dugmesine iki kez basmak sorun degil.
         */
        post: operations["issue_to_todo_api_projects__project_id__github_issues_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}/journal": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project Journal */
        get: operations["project_journal_api_projects__project_id__journal_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}/journal/{day}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Project Journal Note */
        put: operations["put_project_journal_note_api_projects__project_id__journal__day__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}/milestones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Milestone */
        post: operations["add_milestone_api_projects__project_id__milestones_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/projects/{project_id}/todos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project Todos */
        get: operations["project_todos_api_projects__project_id__todos_get"];
        put?: never;
        /** Add Project Todo */
        post: operations["add_project_todo_api_projects__project_id__todos_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/recurring-payments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Recurring */
        get: operations["recurring_api_recurring_payments_get"];
        put?: never;
        /** Add Recurring */
        post: operations["add_recurring_api_recurring_payments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/recurring-payments/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Recurring */
        delete: operations["delete_recurring_api_recurring_payments__item_id__delete"];
        options?: never;
        head?: never;
        /** Patch Recurring */
        patch: operations["patch_recurring_api_recurring_payments__item_id__patch"];
        trace?: never;
    };
    "/api/recurring-payments/{item_id}/pay": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pay */
        post: operations["pay_api_recurring_payments__item_id__pay_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/registry/entity-types": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Registry Entity Types
         * @description Tip -> etiket/rota/ikon kayit defteri (AGENTS.md kural 13). Frontend
         *     bu uctan beslenir; tip->rota sabiti YAZMAZ.
         */
        get: operations["registry_entity_types_api_registry_entity_types_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/registry/event-verbs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Registry Event Verbs
         * @description Event verb -> etiket kayit defteri.
         */
        get: operations["registry_event_verbs_api_registry_event_verbs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/requirements/{requirement_id}/document": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Bind Requirement Document */
        patch: operations["bind_requirement_document_api_requirements__requirement_id__document_patch"];
        trace?: never;
    };
    "/api/reviews": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Reviews */
        get: operations["list_reviews_api_reviews_get"];
        put?: never;
        /** Create Review */
        post: operations["create_review_api_reviews_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/reviews/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Preview */
        get: operations["preview_api_reviews_preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/feeds": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Feeds */
        get: operations["list_feeds_api_rss_feeds_get"];
        put?: never;
        /** Add Feed */
        post: operations["add_feed_api_rss_feeds_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/feeds/{feed_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Feed */
        delete: operations["delete_feed_api_rss_feeds__feed_id__delete"];
        options?: never;
        head?: never;
        /** Update Feed */
        patch: operations["update_feed_api_rss_feeds__feed_id__patch"];
        trace?: never;
    };
    "/api/rss/feeds/{feed_id}/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh Feed
         * @description Tek feed'i simdi cek. Worker'i beklemeden test etmek icin.
         */
        post: operations["refresh_feed_api_rss_feeds__feed_id__refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Opml
         * @description OPML disa aktarimi (Feedly/Inoreader/NetNewsWire) -> feed'ler.
         *
         *     Kategori, feed'i saran outline grubunun basligindan gelir.
         */
        post: operations["import_opml_api_rss_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items_api_rss_items_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Item
         * @description Okuma bolmesi detayi -- content burada dolu gelir (liste hafif kalir).
         */
        get: operations["get_item_api_rss_items__item_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/items/{item_id}/fulltext": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Item Full Text
         * @description Tam metin: cache'te varsa dondur, yoksa talebe bagli fetch edip kalicilastirir.
         *
         *     Fetch basarisiz / cikarilamazsa full_text: null doner (hata mesaji yok;
         *     istemci butonu tekrar gosterir). Ayni item'a eszamanli cift istek null gorur.
         */
        get: operations["item_full_text_api_rss_items__item_id__fulltext_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/items/{item_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark Read */
        post: operations["mark_read_api_rss_items__item_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/items/{item_id}/save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Save Item
         * @description Item -> bookmark + link(feed_item -> bookmark, 'saved_from').
         */
        post: operations["save_item_api_rss_items__item_id__save_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/read-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark All Read */
        post: operations["mark_all_read_api_rss_read_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/refresh-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh All
         * @description Suresi gelmis tum feed'leri arka planda ceker; yanit hemen doner.
         *
         *     Cekim bir kez kuyruklanir; tekrar tiklamak suresi gelmemis feed bulamaz.
         */
        post: operations["refresh_all_api_rss_refresh_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/rss/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Rss Stats */
        get: operations["rss_stats_api_rss_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search */
        get: operations["search_api_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Settings */
        get: operations["settings_api_settings_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/settings/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reset Settings
         * @description Tum kullanici ayarlarini siler: GET /settings yeniden varsayilan doner.
         *
         *     OAuth token'lari AYRI tabloda (integrations.oauth_token) -- bu uc onlara
         *     dokunmaz. Worker kalp atisi ve elle senkron durumu sistem durumudur,
         *     silinirse panel "bilinmiyor" gosterir; onlar korunur.
         */
        post: operations["reset_settings_api_settings_reset_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/settings/{key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Setting */
        put: operations["put_setting_api_settings__key__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/cache": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Source Cache Stats
         * @description Ozet: boyut, dosya sayisi, en eski kayit, host basina kullanim.
         */
        get: operations["source_cache_stats_api_sources_cache_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/cache/clear": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Source Cache Clear
         * @description On-disk scraper onbellegini temizle; acik onay ister.
         */
        post: operations["source_cache_clear_api_sources_cache_clear_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/cache/prune": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Source Cache Prune
         * @description TTL ve butce sinirlarina gore buda; sinir verilmezse config varsayilani.
         */
        post: operations["source_cache_prune_api_sources_cache_prune_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Source Catalog
         * @description Kaynak katalogu: sinif, tahmini sure ve devre kesici durumu.
         */
        get: operations["source_catalog_api_sources_catalog_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/coverage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Source Coverage
         * @description Kaynak kapsam matrisi: hangi kurumu takip ediyoruz, hangisi eksik?
         *
         *     Her satir bir kaynaktir; resmi/ikincil ayrimi, son basarili kosu, son yeni
         *     icerik, ortalama yayin araligi ve ust uste bos kosu sayisi tek yerde durur.
         */
        get: operations["source_coverage_api_sources_coverage_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Source Health
         * @description Her kaynagin son kosumu. 'empty' veya 'error' goruyorsan bir sey kirilmis.
         */
        get: operations["source_health_api_sources_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/jobhunter/config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Jobhunter Config */
        get: operations["jobhunter_config_api_sources_jobhunter_config_get"];
        /**
         * Jobhunter Config Update
         * @description Uyum profili ve dengeler. config.yaml a yazilir ve SICAK yuklenir.
         *
         *     Yeni skorlar bir sonraki senkron turunda gecerli olur (forkjob_port.SCORING
         *     aninda guncellenir).
         */
        put: operations["jobhunter_config_update_api_sources_jobhunter_config_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/jobhunter/env": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Jobhunter Env
         * @description LinkedIn direct/proxy ayarlarinin gercek durumu.
         *
         *     `allow_direct` bir guvenlik anahtaridir: yalnizca ortam degiskeni acikca
         *     acarsa true olur (bkz. `env_flag`). Yanlis yazilmis `linkein_allow_direct`
         *     alani eski istemciler icin ayni degerle korunur.
         */
        get: operations["jobhunter_env_api_sources_jobhunter_env_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/jobhunter/linkedin-profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Jobhunter Linkedin Profiles */
        get: operations["jobhunter_linkedin_profiles_api_sources_jobhunter_linkedin_profiles_get"];
        /**
         * Jobhunter Linkedin Profiles Save
         * @description Kullanici LinkedIn arama profillerinin tamami -- atomik YAML yazimi.
         */
        put: operations["jobhunter_linkedin_profiles_save_api_sources_jobhunter_linkedin_profiles_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh Sources
         * @description Secmeli ya da toplu cekim.
         *
         *     source_ids verilirse yalnizca onlar (kullanici ne sectiyse, opt-in dahil);
         *     aksi halde `mode`: `critical` yalnizca resmi/hizli kaynaklari, `general`
         *     (varsayilan) opt-in/yavas kaynaklar haric tumunu, `full` ise katalogun
         *     tamamini kosar. Her durumda critical -> normal -> slow_optin sirasi
         *     korunur. API yalnizca kalici batch olusturur; cekimi API arka plan gorevi
         *     tuketir; worker acikken ayni kalici kuyrugu paylasir.
         */
        post: operations["refresh_sources_api_sources_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Source Runs */
        get: operations["source_runs_api_sources_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Sync Status
         * @description Aktif manuel batch ve kaynak bazli kesin ilerleme.
         *
         *     Okuma ayni zamanda uzlastirir: worker kapaliyken terk edilmis sahiplikler
         *     geri alinir ve kuyruk bos kalmasin diye (taze bir drain yoksa) arka planda
         *     tuketim devralinir. Boylece batch asla sonsuza kadar `running` kalmaz.
         */
        get: operations["sync_status_api_sources_sync_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/sync/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sync History */
        get: operations["sync_history_api_sources_sync_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/{source_id}/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh Source */
        post: operations["refresh_source_api_sources__source_id__refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/statistics/monthly": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Statistics Monthly */
        get: operations["statistics_monthly_api_statistics_monthly_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/statistics/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Statistics Summary */
        get: operations["statistics_summary_api_statistics_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/areas": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Areas */
        get: operations["areas_api_study_areas_get"];
        put?: never;
        /** Add Area */
        post: operations["add_area_api_study_areas_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/areas/{area_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Area */
        delete: operations["delete_area_api_study_areas__area_id__delete"];
        options?: never;
        head?: never;
        /** Patch Area */
        patch: operations["patch_area_api_study_areas__area_id__patch"];
        trace?: never;
    };
    "/api/study/areas/{area_id}/tree": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Area Tree */
        get: operations["area_tree_api_study_areas__area_id__tree_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Topics
         * @description Konu agacini JSON'dan kurar/gunceller (atomik: tek commit).
         *
         *     Yeniden yuklenebilir: ayni baslik ayni ebeveyn altinda eslesir, kopya
         *     olusmaz. `prune=true` agacta olmayani SILMEZ, arsivler.
         */
        post: operations["import_topics_api_study_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/import/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Preview
         * @description Yazmadan ne olacagini soyler (creates/updates/matches/sayaclar).
         */
        post: operations["import_preview_api_study_import_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/resources/attach-bookmark": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Attach Bookmark
         * @description Yer imini ogrenme kaynagina baglar (kopyalamaz; ayni bag idempotent).
         */
        post: operations["attach_bookmark_api_study_resources_attach_bookmark_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Review Queue */
        get: operations["review_queue_api_study_review_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/stale": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stale */
        get: operations["stale_api_study_stale_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Study Stats */
        get: operations["study_stats_api_study_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Topics
         * @description Alan agaci (ic ice, ESKI sekil -- yol degismedi).
         */
        get: operations["topics_api_study_topics_get"];
        put?: never;
        /** Add Topic */
        post: operations["add_topic_api_study_topics_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics/{topic_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topic */
        get: operations["topic_api_study_topics__topic_id__get"];
        put?: never;
        post?: never;
        /** Delete Topic */
        delete: operations["delete_topic_api_study_topics__topic_id__delete"];
        options?: never;
        head?: never;
        /** Patch Topic */
        patch: operations["patch_topic_api_study_topics__topic_id__patch"];
        trace?: never;
    };
    "/api/study/topics/{topic_id}/impact": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topic Impact */
        get: operations["topic_impact_api_study_topics__topic_id__impact_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics/{topic_id}/move": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move Topic */
        post: operations["move_topic_api_study_topics__topic_id__move_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics/{topic_id}/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topic Progress */
        get: operations["topic_progress_api_study_topics__topic_id__progress_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics/{topic_id}/resources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topic Resources */
        get: operations["topic_resources_api_study_topics__topic_id__resources_get"];
        put?: never;
        /** Add Resource */
        post: operations["add_resource_api_study_topics__topic_id__resources_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics/{topic_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review Topic */
        post: operations["review_topic_api_study_topics__topic_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/study/topics/{topic_id}/todos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Topic Todo
         * @description Konudan gorev + `prepares_for` bagini tek istekte uretir (Faz 17).
         *
         *     Idempotent: konunun acik gorevi varsa yenisi acilmaz (`created: false`);
         *     `force=true` ikinci gorevi uretir. Go vde ortak TodoIn sozlesmesidir.
         */
        post: operations["create_topic_todo_api_study_topics__topic_id__todos_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Manual Refresh Status */
        get: operations["manual_refresh_status_api_system_refresh_get"];
        put?: never;
        /**
         * Manual Refresh
         * @description Manuel yenileme baslat.
         *
         *     Kapsam kritik/standart/tam secilebilir. Zaten calisan bir yenileme varsa
         *     ikincisi baslatilmaz; ayni istek yanitiyla mevcut durum doner.
         */
        post: operations["manual_refresh_api_system_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * System Stats
         * @description Panel icin sunucu sagligi: CPU, RAM, disk, uptime.
         *
         *     Harici bagimliliksiz -- /proc okunur. forkOS'un uzerinde kostugu
         *     makineyi (Linux VM ya da host) yansitir, tek bir container'i degil.
         *
         *     CPU yuzdesi /proc/stat farkindan hesaplanir. Onceden `loadavg[0]/cekirdek`
         *     gosteriliyordu; o bir kuyruk uzunlugu orani, kullanim yuzdesi degil --
         *     bos bir makinede bile yuksek, tam dolu bir makinede bile dusuk cikabilir.
         */
        get: operations["system_stats_api_system_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tags */
        get: operations["list_tags_api_tags_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/today/agenda": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Agenda */
        get: operations["agenda_api_today_agenda_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/todos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Todos */
        get: operations["list_todos_api_todos_get"];
        put?: never;
        /** Create Todo */
        post: operations["create_todo_api_todos_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/todos/{todo_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Todo */
        delete: operations["delete_todo_api_todos__todo_id__delete"];
        options?: never;
        head?: never;
        /** Update Todo */
        patch: operations["update_todo_api_todos__todo_id__patch"];
        trace?: never;
    };
    "/api/todos/{todo_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Todo */
        post: operations["complete_todo_api_todos__todo_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/views": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Views
         * @description Kayitli gorunumler. Sira: sabitlenenler once, sonra konum, sonra id.
         */
        get: operations["list_views_api_views_get"];
        put?: never;
        /**
         * Create View
         * @description Yeni gorunum. position = modul icindeki en buyuk + 1.
         */
        post: operations["create_view_api_views_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/views/{view_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete View */
        delete: operations["delete_view_api_views__view_id__delete"];
        options?: never;
        head?: never;
        /**
         * Patch View
         * @description Verilen alanlari gunceller; pinned=true ise view en on konuma cekilir.
         */
        patch: operations["patch_view_api_views__view_id__patch"];
        trace?: never;
    };
    "/api/weather/forecast": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Weather Forecast
         * @description Open-Meteo tahmini -- arayuzun bekledigi alanlar aynen gecirilir.
         */
        get: operations["weather_forecast_api_weather_forecast_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/weather/geocode": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Weather Geocode
         * @description Sehir adi -> koordinat; lat/lon verilirse ters yon (koordinat -> ad).
         *
         *     Ters mod, tarayici konum izniyle bulunan noktayi Ayarlar'da ada cevirmek
         *     icin. Ikisi de ayni dis servisi kullanir, tek ucta toplanir.
         */
        get: operations["weather_geocode_api_weather_geocode_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AgendaRow */
        AgendaRow: {
            /** Action */
            action?: ("complete_todo" | "mark_rss_read" | "log_media") | null;
            /** Children */
            children?: components["schemas"]["AgendaRow"][];
            /**
             * Completed
             * @default false
             */
            completed: boolean;
            /**
             * Context Only
             * @default false
             */
            context_only: boolean;
            /** Cover Url */
            cover_url?: string | null;
            /** Duration Min */
            duration_min?: number | null;
            /** Entity Type */
            entity_type?: string | null;
            /** Feed Title */
            feed_title?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "calendar" | "todo" | "rss" | "media" | "opportunity" | "interview" | "payment" | "study" | "flashcard";
            /** Media Kind */
            media_kind?: string | null;
            /** Media Status */
            media_status?: string | null;
            /** Next Review At */
            next_review_at?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Progress Label */
            progress_label?: string | null;
            /** Project Title */
            project_title?: string | null;
            /**
             * Read Only
             * @default false
             */
            read_only: boolean;
            /** Recur */
            recur?: ("daily" | "weekdays" | "weekly" | "monthly") | null;
            /** Slot Id */
            slot_id?: string | null;
            /**
             * Source
             * @enum {string}
             */
            source: "calendar" | "planned" | "due" | "routine" | "suggestion";
            /** Starts At */
            starts_at?: string | null;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** AgendaSuggestions */
        AgendaSuggestions: {
            /** Flashcards */
            flashcards?: components["schemas"]["AgendaRow"][];
            /** Media */
            media?: components["schemas"]["AgendaRow"][];
            /** Rss */
            rss?: components["schemas"]["AgendaRow"][];
            /** Study */
            study?: components["schemas"]["AgendaRow"][];
            /** Todos */
            todos?: components["schemas"]["AgendaRow"][];
        };
        /** AncestorOut */
        AncestorOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
        };
        /** ApplicationIn */
        ApplicationIn: {
            /** Company Research */
            company_research?: string | null;
            /** Cover Letter */
            cover_letter?: string | null;
            /** Cv Document Id */
            cv_document_id?: string | null;
            /** Note */
            note?: string | null;
            /** Salary Expectation */
            salary_expectation?: string | null;
        };
        /** ApplicationOut */
        ApplicationOut: {
            /** Company Research */
            company_research?: string | null;
            /** Cover Letter */
            cover_letter?: string | null;
            /** Created At */
            created_at?: string | null;
            /** Cv Document Id */
            cv_document_id?: string | null;
            /** Cv Modified At */
            cv_modified_at?: string | null;
            /** Cv Title */
            cv_title?: string | null;
            /** Note */
            note?: string | null;
            /**
             * Opportunity Id
             * Format: uuid
             */
            opportunity_id: string;
            /**
             * Posting Snapshot
             * @default {}
             */
            posting_snapshot: {
                [key: string]: unknown;
            };
            /** Salary Expectation */
            salary_expectation?: string | null;
            /**
             * Status
             * @default applied
             */
            status: string;
            /** Status Changed At */
            status_changed_at?: string | null;
            /** Updated At */
            updated_at?: string | null;
        };
        /** ApplicationReviewStats */
        ApplicationReviewStats: {
            /** Discovered */
            discovered: number;
            /** Updated */
            updated: number;
        };
        /** ApplicationTimelineOut */
        ApplicationTimelineOut: {
            /** Entries */
            entries: components["schemas"]["TimelineEntryOut"][];
            /**
             * Opportunity Id
             * Format: uuid
             */
            opportunity_id: string;
        };
        /**
         * ApplyIn
         * @description Ilk basvuru: durum 'applied' yapar, snapshot'i birlikte alir.
         */
        ApplyIn: {
            /** Company Research */
            company_research?: string | null;
            /** Cover Letter */
            cover_letter?: string | null;
            /** Cv Document Id */
            cv_document_id?: string | null;
            /** Note */
            note?: string | null;
            /** Salary Expectation */
            salary_expectation?: string | null;
        };
        /** AreaIn */
        AreaIn: {
            /** Color */
            color?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
        };
        /** AreaPatch */
        AreaPatch: {
            /** Active */
            active?: boolean | null;
            /** Archived */
            archived?: boolean | null;
            /** Color */
            color?: string | null;
            /** Position */
            position?: number | null;
            /** Title */
            title?: string | null;
        };
        /** AttachBookmarkIn */
        AttachBookmarkIn: {
            /**
             * Bookmark Id
             * Format: uuid
             */
            bookmark_id: string;
            /**
             * Topic Id
             * Format: uuid
             */
            topic_id: string;
        };
        /** Body_import_cards_api_flashcard_import_post */
        Body_import_cards_api_flashcard_import_post: {
            /** File */
            file: string;
        };
        /** Body_import_career_connections_api_career_connections_import_post */
        Body_import_career_connections_api_career_connections_import_post: {
            /** File */
            file: string;
        };
        /** Body_import_opml_api_rss_import_post */
        Body_import_opml_api_rss_import_post: {
            /** File */
            file: string;
        };
        /** Body_inspect_backup_api_backup_inspect_post */
        Body_inspect_backup_api_backup_inspect_post: {
            /** File */
            file: string;
        };
        /** Body_restore_backup_api_backup_restore_post */
        Body_restore_backup_api_backup_restore_post: {
            /** File */
            file: string;
        };
        /** Body_upload_attachment_api_notes__note_id__attachments_post */
        Body_upload_attachment_api_notes__note_id__attachments_post: {
            /** File */
            file: string;
        };
        /** Body_upload_document_api_documents_upload_post */
        Body_upload_document_api_documents_upload_post: {
            /**
             * Category
             * @default cv
             */
            category: string;
            /** File */
            file: string;
        };
        /** BookmarkBulkActionIn */
        BookmarkBulkActionIn: {
            /**
             * Action
             * @enum {string}
             */
            action: "move" | "delete" | "tag" | "read_status";
            /** Bookmark Ids */
            bookmark_ids: string[];
            /** Collection */
            collection?: string | null;
            /** Read Status */
            read_status?: string | null;
            /** Tags */
            tags?: string[] | null;
        };
        /** BookmarkBulkActionResult */
        BookmarkBulkActionResult: {
            /** Action */
            action: string;
            /** Affected */
            affected: number;
        };
        /** BookmarkFullTextOut */
        BookmarkFullTextOut: {
            /** Author */
            author?: string | null;
            /** Content Html */
            content_html?: string | null;
            /** Content Text */
            content_text?: string | null;
            /** Favicon Url */
            favicon_url?: string | null;
            /** Hero Image Url */
            hero_image_url?: string | null;
            /**
             * Highlights
             * @default []
             */
            highlights: components["schemas"]["BookmarkHighlightOut"][];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Published At */
            published_at?: string | null;
            /**
             * Reading Time Min
             * @default 1
             */
            reading_time_min: number;
            /**
             * Scroll Progress
             * @default 0
             */
            scroll_progress: number;
            /** Title */
            title: string;
            /** Url */
            url: string;
            /**
             * Word Count
             * @default 0
             */
            word_count: number;
        };
        /** BookmarkHighlightIn */
        BookmarkHighlightIn: {
            /**
             * Anchor Index
             * @default 0
             */
            anchor_index: number;
            /**
             * Color
             * @default yellow
             */
            color: string;
            /** Note */
            note?: string | null;
            /** Text */
            text: string;
        };
        /** BookmarkHighlightOut */
        BookmarkHighlightOut: {
            /**
             * Anchor Index
             * @default 0
             */
            anchor_index: number;
            /**
             * Bookmark Id
             * Format: uuid
             */
            bookmark_id: string;
            /**
             * Color
             * @default yellow
             */
            color: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Note */
            note?: string | null;
            /** Text */
            text: string;
        };
        /** BookmarkOut */
        BookmarkOut: {
            /** Author */
            author?: string | null;
            /** Collection */
            collection: string;
            /** Description */
            description?: string | null;
            /** Existing Collection */
            existing_collection?: string | null;
            /** Favicon Url */
            favicon_url?: string | null;
            /** Favorite */
            favorite: boolean;
            /** Hero Image Url */
            hero_image_url?: string | null;
            /**
             * Highlights Count
             * @default 0
             */
            highlights_count: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Is Duplicate
             * @default false
             */
            is_duplicate: boolean;
            /** Note */
            note?: string | null;
            /** Published At */
            published_at?: string | null;
            /** Queue Kind */
            queue_kind?: string | null;
            /** Read Status */
            read_status: string;
            /**
             * Reading Time Min
             * @default 1
             */
            reading_time_min: number;
            /**
             * Saved At
             * Format: date-time
             */
            saved_at: string;
            /**
             * Scroll Progress
             * @default 0
             */
            scroll_progress: number;
            /** Selection */
            selection?: string | null;
            /** Source */
            source: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Title */
            title: string;
            /** Url */
            url: string;
            /**
             * Word Count
             * @default 0
             */
            word_count: number;
        };
        /** BookmarkProgressUpdate */
        BookmarkProgressUpdate: {
            /** Scroll Progress */
            scroll_progress: number;
        };
        /** BookmarkStats */
        BookmarkStats: {
            /** Collections */
            collections: components["schemas"]["CollectionCount"][];
            /** Inbox */
            inbox: number;
            /** Saved Today */
            saved_today: number;
            /** Total */
            total: number;
            /** Unread */
            unread: number;
        };
        /**
         * BookmarkUpdate
         * @description Kismi guncelleme. Verilmeyen alana dokunulmaz.
         */
        BookmarkUpdate: {
            /** Author */
            author?: string | null;
            /** Collection */
            collection?: string | null;
            /** Description */
            description?: string | null;
            /** Favicon Url */
            favicon_url?: string | null;
            /** Favorite */
            favorite?: boolean | null;
            /** Hero Image Url */
            hero_image_url?: string | null;
            /** Note */
            note?: string | null;
            /** Queue Kind */
            queue_kind?: string | null;
            /** Read Status */
            read_status?: string | null;
            /** Reading Time Min */
            reading_time_min?: number | null;
            /** Scroll Progress */
            scroll_progress?: number | null;
            /** Tags */
            tags?: string[] | null;
            /** Title */
            title?: string | null;
        };
        /** CacheClearIn */
        CacheClearIn: {
            /**
             * Confirm
             * @default false
             */
            confirm: boolean;
        };
        /** CachePruneIn */
        CachePruneIn: {
            /** Max Age Seconds */
            max_age_seconds?: number | null;
            /** Max Bytes */
            max_bytes?: number | null;
        };
        /**
         * CaptureIn
         * @description Extension ve Life OS ici quick capture ayni endpoint'i kullanir.
         */
        CaptureIn: {
            /** Author */
            author?: string | null;
            /** Client Uuid */
            client_uuid?: string | null;
            /**
             * Collection
             * @default inbox
             */
            collection: string;
            /** Description */
            description?: string | null;
            /** Favicon Url */
            favicon_url?: string | null;
            /** Hero Image Url */
            hero_image_url?: string | null;
            /** Note */
            note?: string | null;
            /** Reading Time Min */
            reading_time_min?: number | null;
            /** Selection */
            selection?: string | null;
            /**
             * Source
             * @default extension
             */
            source: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url: string;
            /** Word Count */
            word_count?: number | null;
        };
        /** CaptureResult */
        CaptureResult: {
            /**
             * Collection
             * @default inbox
             */
            collection: string;
            /**
             * Duplicate
             * @default false
             */
            duplicate: boolean;
            /** Existing Id */
            existing_id?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
        };
        /** CaptureReviewStats */
        CaptureReviewStats: {
            /** Bookmarks */
            bookmarks: number;
            /** Notes */
            notes: number;
            /** Rss Read */
            rss_read: number;
        };
        /** CardIn */
        CardIn: {
            /** Back */
            back: string;
            /** Front */
            front: string;
            /**
             * Reversible
             * @default false
             */
            reversible: boolean;
        };
        /** CardOut */
        CardOut: {
            /** Back */
            back: string;
            /**
             * Deck Id
             * Format: uuid
             */
            deck_id: string;
            /** Due At */
            due_at: string | null;
            /** Ease */
            ease: number;
            /** Front */
            front: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Interval Days */
            interval_days: number;
            /** Lapses */
            lapses: number;
            /** Reps */
            reps: number;
            /** Suspended */
            suspended: boolean;
        };
        /** CardPatch */
        CardPatch: {
            /** Back */
            back?: string | null;
            /** Front */
            front?: string | null;
            /** Suspended */
            suspended?: boolean | null;
        };
        /** CareerConnectionOut */
        CareerConnectionOut: {
            /** Company */
            company?: string | null;
            /** Connected On */
            connected_on?: string | null;
            /** Email */
            email?: string | null;
            /** First Name */
            first_name?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Name */
            last_name?: string | null;
            /** Name */
            name: string;
            /** Position */
            position?: string | null;
            /** Profile Url */
            profile_url?: string | null;
        };
        /** CareerConnectionsImportOut */
        CareerConnectionsImportOut: {
            /** Created */
            created: number;
            /** Skipped */
            skipped: number;
            /** Total Rows */
            total_rows: number;
            /** Updated */
            updated: number;
        };
        /** CareerStoryIn */
        CareerStoryIn: {
            /** Action */
            action?: string | null;
            /**
             * Provenance
             * @default existing
             * @enum {string}
             */
            provenance: "existing" | "supported" | "derived-unverified" | "user-cannot-confirm";
            /** Reflection */
            reflection?: string | null;
            /** Result */
            result?: string | null;
            /** Situation */
            situation?: string | null;
            /** Tags */
            tags?: string[];
            /** Task */
            task?: string | null;
            /** Title */
            title: string;
        };
        /** CareerStoryOut */
        CareerStoryOut: {
            /** Action */
            action?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Provenance
             * @enum {string}
             */
            provenance: "existing" | "supported" | "derived-unverified" | "user-cannot-confirm";
            /** Reflection */
            reflection?: string | null;
            /** Result */
            result?: string | null;
            /** Situation */
            situation?: string | null;
            /** Tags */
            tags?: string[];
            /** Task */
            task?: string | null;
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** CareerStoryPatch */
        CareerStoryPatch: {
            /** Action */
            action?: string | null;
            /** Provenance */
            provenance?: ("existing" | "supported" | "derived-unverified" | "user-cannot-confirm") | null;
            /** Reflection */
            reflection?: string | null;
            /** Result */
            result?: string | null;
            /** Situation */
            situation?: string | null;
            /** Tags */
            tags?: string[] | null;
            /** Task */
            task?: string | null;
            /** Title */
            title?: string | null;
        };
        /** CarryOverIn */
        CarryOverIn: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /**
             * Target
             * Format: date
             */
            target: string;
        };
        /** CollectionCount */
        CollectionCount: {
            /** Collection */
            collection: string;
            /** Count */
            count: number;
        };
        /** CompletedTodo */
        CompletedTodo: {
            /**
             * Completed At
             * Format: date-time
             */
            completed_at: string;
            /** Id */
            id: string | null;
            /** Title */
            title: string;
        };
        /**
         * ContextOut
         * @description Odaklanilabilecek bir kayit: gorev, calisma konusu, kaynak, proje, medya...
         */
        ContextOut: {
            /** Cover Url */
            cover_url?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind?: string | null;
            /** Title */
            title: string;
            /** Type */
            type: string;
        };
        /** ConvertToTaskIn */
        ConvertToTaskIn: {
            /** Due At */
            due_at?: string | null;
            /** Plan Day */
            plan_day?: string | null;
            /**
             * Priority
             * @default 2
             */
            priority: number;
        };
        /**
         * CounterBreakdown
         * @description Bir sayacin uc zaman dilimi: bugun (app gunu), son 7 gun, tum zamanlar.
         */
        CounterBreakdown: {
            /** Today */
            today: number;
            /** Total */
            total: number;
            /** Week */
            week: number;
        };
        /** CourseIn */
        CourseIn: {
            /** Area Ids */
            area_ids?: string[];
            /** Certificate Entity Id */
            certificate_entity_id?: string | null;
            /** Notes */
            notes?: string | null;
            /** Platform */
            platform?: string | null;
            /**
             * Progress Pct
             * @default 0
             */
            progress_pct: number;
            /**
             * Status
             * @default planned
             */
            status: string;
            /** Title */
            title: string;
            /** Topic Ids */
            topic_ids?: string[];
            /** Url */
            url?: string | null;
        };
        /** CourseOut */
        CourseOut: {
            /**
             * Archived
             * @default false
             */
            archived: boolean;
            /** Area Ids */
            area_ids?: string[];
            /** Certificate Entity Id */
            certificate_entity_id?: string | null;
            /** Completed At */
            completed_at?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Notes */
            notes?: string | null;
            /** Platform */
            platform?: string | null;
            /** Progress Pct */
            progress_pct: number;
            /**
             * Resource Count
             * @default 0
             */
            resource_count: number;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
            /** Topic Ids */
            topic_ids?: string[];
            /** Url */
            url?: string | null;
        };
        /** CoursePatch */
        CoursePatch: {
            /** Archived */
            archived?: boolean | null;
            /** Area Ids */
            area_ids?: string[] | null;
            /** Certificate Entity Id */
            certificate_entity_id?: string | null;
            /** Notes */
            notes?: string | null;
            /** Platform */
            platform?: string | null;
            /** Progress Pct */
            progress_pct?: number | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
            /** Topic Ids */
            topic_ids?: string[] | null;
            /** Url */
            url?: string | null;
        };
        /** CoverLetterReviewIn */
        CoverLetterReviewIn: {
            /** Text */
            text: string;
        };
        /** CoverLetterReviewOut */
        CoverLetterReviewOut: {
            /** Flags */
            flags?: string[];
            /** Generic Phrases */
            generic_phrases?: string[];
            /** Matched Story Ids */
            matched_story_ids?: string[];
            /** Score */
            score: number;
            /** Suggestions */
            suggestions?: string[];
        };
        /**
         * CramCardOut
         * @description Cram kuyrugu: kart + ait oldugu deste adi (tek listede gosterilir).
         */
        CramCardOut: {
            /** Back */
            back: string;
            /**
             * Deck Id
             * Format: uuid
             */
            deck_id: string;
            /** Deck Title */
            deck_title: string;
            /** Due At */
            due_at: string | null;
            /** Ease */
            ease: number;
            /** Front */
            front: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Interval Days */
            interval_days: number;
            /** Lapses */
            lapses: number;
            /** Reps */
            reps: number;
            /** Suspended */
            suspended: boolean;
        };
        /** CreateNoteFromBookmarkIn */
        CreateNoteFromBookmarkIn: {
            /** Additional Text */
            additional_text?: string | null;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
        };
        /** DeckIn */
        DeckIn: {
            /** Title */
            title: string;
        };
        /** DeckOut */
        DeckOut: {
            /** Card Count */
            card_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Due Count */
            due_count: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Mature Count
             * @default 0
             */
            mature_count: number;
            /** New Count */
            new_count: number;
            /** Title */
            title: string;
        };
        /** DeckPatch */
        DeckPatch: {
            /** Title */
            title: string;
        };
        /**
         * DocumentUsagesOut
         * @description Bir belgenin bağlı fırsat kullanım listesi.
         */
        DocumentUsagesOut: {
            /**
             * Document Id
             * Format: uuid
             */
            document_id: string;
            /** Usages */
            usages: components["schemas"]["OpportunityUsageOut"][];
        };
        /** EntityOut */
        EntityOut: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Type */
            type: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** EvaluationGateOut */
        EvaluationGateOut: {
            /** Authorized To Work */
            authorized_to_work?: boolean | null;
            /**
             * Geo Mismatch
             * @default false
             */
            geo_mismatch: boolean;
            /**
             * Hard Blocker
             * @default false
             */
            hard_blocker: boolean;
            /** Job Country */
            job_country?: string | null;
            /** Reasons */
            reasons?: string[];
            /**
             * Sponsorship Status
             * @default unstated
             * @enum {string}
             */
            sponsorship_status: "sponsors" | "not_needed" | "unstated" | "no_sponsorship";
        };
        /** EvaluationMatchOut */
        EvaluationMatchOut: {
            /** Evidence */
            evidence: string;
            /** Gap Mitigation */
            gap_mitigation?: string | null;
            /**
             * Match
             * @enum {string}
             */
            match: "strong" | "partial" | "missing";
            /** Requirement */
            requirement: string;
            /** Requirement Id */
            requirement_id: string;
            /** Story Ids */
            story_ids?: string[];
        };
        /** EvaluationRequirementOut */
        EvaluationRequirementOut: {
            /**
             * Evidence
             * @enum {string}
             */
            evidence: "stated" | "structural" | "inferred";
            /** Excerpt */
            excerpt?: string | null;
            /** Id */
            id: string;
            /**
             * Importance
             * @enum {string}
             */
            importance: "critical" | "high" | "meaningful" | "preferred" | "low_signal";
            /** Name */
            name: string;
            /** Terms */
            terms?: string[];
        };
        /** EventOut */
        EventOut: {
            /** Entity Id */
            entity_id: string | null;
            /** Entity Type */
            entity_type: string | null;
            /** Id */
            id: number;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Verb */
            verb: string;
        };
        /** ExpenseIn */
        ExpenseIn: {
            /** Amount */
            amount: number | string;
            /**
             * Category
             * @default other
             */
            category: string;
            /**
             * Currency
             * @default TRY
             */
            currency: string;
            /** Note */
            note?: string | null;
            /**
             * Spent On
             * Format: date
             */
            spent_on?: string;
            /** Sub */
            sub?: string | null;
            /** Title */
            title: string;
        };
        /** ExpensePatch */
        ExpensePatch: {
            /** Amount */
            amount?: number | string | null;
            /** Category */
            category?: string | null;
            /** Currency */
            currency?: string | null;
            /** Note */
            note?: string | null;
            /** Spent On */
            spent_on?: string | null;
            /** Sub */
            sub?: string | null;
            /** Title */
            title?: string | null;
        };
        /** FeedIn */
        FeedIn: {
            /** Category */
            category?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url: string;
        };
        /** FeedItemOut */
        FeedItemOut: {
            /** Author */
            author?: string | null;
            /** Content */
            content?: string | null;
            /**
             * Feed Id
             * Format: uuid
             */
            feed_id: string;
            /**
             * Feed Title
             * @default
             */
            feed_title: string;
            /**
             * Fetched At
             * Format: date-time
             */
            fetched_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Published At */
            published_at?: string | null;
            /** Read At */
            read_at?: string | null;
            /** Saved Bookmark Id */
            saved_bookmark_id?: string | null;
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** FeedOut */
        FeedOut: {
            /** Active */
            active: boolean;
            /** Category */
            category?: string | null;
            /** Error Count */
            error_count: number;
            /** Favicon Url */
            favicon_url?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Fetched At */
            last_fetched_at?: string | null;
            /** Last Status */
            last_status?: string | null;
            /** Site Url */
            site_url?: string | null;
            /** Title */
            title: string;
            /**
             * Unread
             * @default 0
             */
            unread: number;
            /** Url */
            url: string;
        };
        /** FeedUpdate */
        FeedUpdate: {
            /** Active */
            active?: boolean | null;
            /** Category */
            category?: string | null;
            /** Title */
            title?: string | null;
        };
        /**
         * FlashcardReviewStats
         * @description Donemde tekrar edilen kart sayisi + deste kirilimi.
         */
        FlashcardReviewStats: {
            /** Decks */
            decks: {
                [key: string]: number;
            };
            /** Reviewed */
            reviewed: number;
        };
        /** FocusReviewStats */
        FocusReviewStats: {
            /** Active Days */
            active_days: number;
            /** Best Day */
            best_day: string | null;
            /** Best Day Minutes */
            best_day_minutes: number;
            /** Interrupted */
            interrupted: number;
            /** Longest Session */
            longest_session: number;
            /** Minutes */
            minutes: number;
            /** Sessions */
            sessions: number;
        };
        /** FollowupOut */
        FollowupOut: {
            /**
             * Follow Up At
             * Format: date-time
             */
            follow_up_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Note */
            note?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /**
         * FunnelBreakdownRow
         * @description Kirilim satiri. Payda ve paylar UI'da acikca yazilir.
         */
        FunnelBreakdownRow: {
            /** Interview Rate */
            interview_rate?: number | null;
            /** Interviewed */
            interviewed: number;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Offers */
            offers: number;
            /** Responded */
            responded: number;
            /** Response Rate */
            response_rate?: number | null;
            /** Total */
            total: number;
        };
        /** FunnelOut */
        FunnelOut: {
            /** Avg Applied To Interview Days */
            avg_applied_to_interview_days?: number | null;
            /** Avg First Response Days */
            avg_first_response_days?: number | null;
            /** By Country */
            by_country?: components["schemas"]["FunnelBreakdownRow"][];
            /** By Cv */
            by_cv?: components["schemas"]["FunnelBreakdownRow"][];
            /** By Role */
            by_role?: components["schemas"]["FunnelBreakdownRow"][];
            /** By Source */
            by_source?: components["schemas"]["FunnelBreakdownRow"][];
            /** By Status */
            by_status: components["schemas"]["FunnelRow"][];
            /** By Work Mode */
            by_work_mode?: components["schemas"]["FunnelBreakdownRow"][];
            /** Conversions */
            conversions: {
                [key: string]: number | null;
            };
            /** Monthly Volume */
            monthly_volume?: components["schemas"]["FunnelVolumeRow"][];
            /** Rejection Reasons */
            rejection_reasons: {
                [key: string]: unknown;
            }[];
            /** Total */
            total: number;
            /** Tracked */
            tracked: number;
            /** Weekly Volume */
            weekly_volume?: components["schemas"]["FunnelVolumeRow"][];
        };
        /** FunnelRow */
        FunnelRow: {
            /** Count */
            count: number;
            /** Status */
            status: string;
        };
        /** FunnelVolumeRow */
        FunnelVolumeRow: {
            /** Applied */
            applied: number;
            /** Period */
            period: string;
        };
        /** GeocodeOut */
        GeocodeOut: {
            /** Admin1 */
            admin1?: string | null;
            /** Country */
            country?: string | null;
            /** Latitude */
            latitude: number;
            /** Longitude */
            longitude: number;
            /** Name */
            name: string;
        };
        /** GithubCredentialsIn */
        GithubCredentialsIn: {
            /** Login */
            login: string;
            /** Token */
            token: string;
        };
        /** GithubReviewStats */
        GithubReviewStats: {
            /** Commits */
            commits: number;
            /** Repos */
            repos: {
                [key: string]: number;
            };
        };
        /** GlobalMetadataSearchOut */
        GlobalMetadataSearchOut: {
            /**
             * Cached
             * @default false
             */
            cached: boolean;
            /** Results */
            results: components["schemas"]["MetadataResult"][];
            /** Warnings */
            warnings: components["schemas"]["MetadataSearchWarning"][];
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HistoryOut */
        HistoryOut: {
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** From Status */
            from_status?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Note */
            note?: string | null;
            /**
             * Scope
             * @default application
             */
            scope: string;
            /** To Status */
            to_status: string;
        };
        /** ImportAreaOut */
        ImportAreaOut: {
            /**
             * Exists
             * @default false
             */
            exists: boolean;
            /** Id */
            id?: string | null;
            /** Title */
            title: string;
        };
        /** ImportConflictOut */
        ImportConflictOut: {
            /** Path */
            path: string;
            /** Reason */
            reason: string;
        };
        /** ImportNodePreview */
        ImportNodePreview: {
            /** Changes */
            changes?: string[];
            /** Path */
            path: string;
            /**
             * Resources
             * @default 0
             */
            resources: number;
            /**
             * Status
             * @default not_started
             */
            status: string;
            /** Title */
            title: string;
        };
        /** ImportOut */
        ImportOut: {
            /** Added */
            added: number;
            /**
             * Deck Id
             * Format: uuid
             */
            deck_id: string;
            /** Deck Title */
            deck_title: string;
            /** Skipped */
            skipped: number;
        };
        /** ImportPreviewOut */
        ImportPreviewOut: {
            area: components["schemas"]["ImportAreaOut"];
            /** Conflicts */
            conflicts?: components["schemas"]["ImportConflictOut"][];
            /** Creates */
            creates?: components["schemas"]["ImportNodePreview"][];
            /** Invalid */
            invalid?: components["schemas"]["ImportConflictOut"][];
            /** Matches */
            matches?: components["schemas"]["ImportNodePreview"][];
            /**
             * Resources Duplicate
             * @default 0
             */
            resources_duplicate: number;
            /**
             * Resources New
             * @default 0
             */
            resources_new: number;
            /** Suggested Prefix */
            suggested_prefix?: string | null;
            totals: components["schemas"]["ImportTotalsOut"];
            /** Updates */
            updates?: components["schemas"]["ImportNodePreview"][];
        };
        /** ImportResult */
        ImportResult: {
            /** Added */
            added: number;
            /**
             * Feeds
             * @default []
             */
            feeds: string[];
            /** Skipped */
            skipped: number;
        };
        /** ImportTotalsOut */
        ImportTotalsOut: {
            /**
             * Creates
             * @default 0
             */
            creates: number;
            /**
             * Depth
             * @default 0
             */
            depth: number;
            /**
             * Matches
             * @default 0
             */
            matches: number;
            /**
             * Nodes
             * @default 0
             */
            nodes: number;
            /**
             * Updates
             * @default 0
             */
            updates: number;
        };
        /** IncomeIn */
        IncomeIn: {
            /** Amount */
            amount: number | string;
            /**
             * Category
             * @default salary
             */
            category: string;
            /**
             * Currency
             * @default TRY
             */
            currency: string;
            /** Note */
            note?: string | null;
            /**
             * Received On
             * Format: date
             */
            received_on?: string;
            /** Title */
            title: string;
        };
        /** IncomePatch */
        IncomePatch: {
            /** Amount */
            amount?: number | string | null;
            /** Category */
            category?: string | null;
            /** Currency */
            currency?: string | null;
            /** Note */
            note?: string | null;
            /** Received On */
            received_on?: string | null;
            /** Title */
            title?: string | null;
        };
        /** InterviewIn */
        InterviewIn: {
            /** Duration Min */
            duration_min?: number | null;
            /** Mode */
            mode?: string | null;
            /** Notes */
            notes?: string | null;
            /** Outcome */
            outcome?: string | null;
            /** Salary Stated */
            salary_stated?: string | null;
            /** Scheduled At */
            scheduled_at?: string | null;
            /**
             * Stage
             * @default genel
             */
            stage: string;
        };
        /** InterviewOut */
        InterviewOut: {
            /** Duration Min */
            duration_min?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Mode */
            mode?: string | null;
            /** Notes */
            notes?: string | null;
            /**
             * Opportunity Id
             * Format: uuid
             */
            opportunity_id: string;
            /** Outcome */
            outcome?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Salary Stated */
            salary_stated?: string | null;
            /** Scheduled At */
            scheduled_at?: string | null;
            /** Stage */
            stage: string;
        };
        /** IssueToTodoIn */
        IssueToTodoIn: {
            /** Number */
            number: number;
        };
        /** LinkIn */
        LinkIn: {
            /**
             * From Id
             * Format: uuid
             */
            from_id: string;
            /**
             * Relation
             * @default related
             */
            relation: string;
            /**
             * To Id
             * Format: uuid
             */
            to_id: string;
        };
        /**
         * ManualRefreshIn
         * @description Yenileme kapsami. Govde verilmezse `standard`.
         */
        ManualRefreshIn: {
            /**
             * Scope
             * @default standard
             * @enum {string}
             */
            scope: "critical" | "standard" | "full";
        };
        /** ManualRefreshOut */
        ManualRefreshOut: {
            /** Batch Id */
            batch_id?: string | null;
            /** Errors */
            errors?: string[];
            /** Finished At */
            finished_at?: string | null;
            /** Results */
            results?: {
                [key: string]: number;
            };
            /**
             * Scope
             * @default standard
             */
            scope: string;
            /**
             * Started
             * @default false
             */
            started: boolean;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
        };
        /** MediaArtworkPruneOut */
        MediaArtworkPruneOut: {
            /** Freed Bytes */
            freed_bytes: number;
            /** Removed */
            removed: number;
        };
        /** MediaArtworkStatsOut */
        MediaArtworkStatsOut: {
            /** Bytes */
            bytes: number;
            /** Files */
            files: number;
            /** Max Bytes */
            max_bytes: number;
        };
        /** MediaBusiestDayOut */
        MediaBusiestDayOut: {
            /** Count */
            count: number;
            /** Day */
            day: string;
        };
        /** MediaCollectionDetailOut */
        MediaCollectionDetailOut: {
            collection: components["schemas"]["MediaCollectionOut"];
            /** Items */
            items: components["schemas"]["MediaItemOut"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /** Total */
            total: number;
        };
        /** MediaCollectionIn */
        MediaCollectionIn: {
            /** Color */
            color?: string | null;
            /** Description */
            description?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
        };
        /** MediaCollectionOut */
        MediaCollectionOut: {
            /** Color */
            color?: string | null;
            /** Covers */
            covers?: string[];
            /** Created At */
            created_at?: string | null;
            /** Description */
            description?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Item Count
             * @default 0
             */
            item_count: number;
            /** Position */
            position: number;
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** MediaCollectionUpdate */
        MediaCollectionUpdate: {
            /** Color */
            color?: string | null;
            /** Description */
            description?: string | null;
            /** Position */
            position?: number | null;
            /** Title */
            title?: string | null;
        };
        /** MediaConsumptionIn */
        MediaConsumptionIn: {
            /** Action */
            action: string;
            /** Amount */
            amount?: number | null;
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /** Duration Min */
            duration_min?: number | null;
            /** Measure */
            measure?: string | null;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            };
            /** Note */
            note?: string | null;
            /** Occurred At */
            occurred_at?: string | null;
            /** Progress After */
            progress_after?: number | null;
            /** Unit Id */
            unit_id?: string | null;
        };
        /** MediaConsumptionOut */
        MediaConsumptionOut: {
            /** Action */
            action: string;
            /** Amount */
            amount?: number | null;
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Cycle Id
             * Format: uuid
             */
            cycle_id: string;
            /** Duration Min */
            duration_min?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Measure */
            measure?: string | null;
            /**
             * Media Id
             * Format: uuid
             */
            media_id: string;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            };
            /** Note */
            note?: string | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Progress After */
            progress_after?: number | null;
            /** Unit Id */
            unit_id?: string | null;
        };
        /** MediaConsumptionPageOut */
        MediaConsumptionPageOut: {
            /** Items */
            items: components["schemas"]["MediaConsumptionOut"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /** Total */
            total: number;
        };
        /** MediaConversionOut */
        MediaConversionOut: {
            /**
             * Completed
             * @default 0
             */
            completed: number;
            /**
             * Planned
             * @default 0
             */
            planned: number;
            /**
             * Started
             * @default 0
             */
            started: number;
        };
        /** MediaCycleOut */
        MediaCycleOut: {
            /** Completed At */
            completed_at?: string | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Caught Up At */
            last_caught_up_at?: string | null;
            /**
             * Media Id
             * Format: uuid
             */
            media_id: string;
            /** Notes */
            notes?: string | null;
            /** Ordinal */
            ordinal: number;
            /** Score */
            score?: number | null;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Status */
            status: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /** MediaCycleStart */
        MediaCycleStart: {
            /** Notes */
            notes?: string | null;
            /** Started At */
            started_at?: string | null;
        };
        /**
         * MediaDashboardOut
         * @description Istatistik sayfasinin TEK istegi: ozet + devam + yaklasan + son tuketimler.
         *
         *     Neden toplayici: ayni veri icin ayri uclara ayri istek atmak (ve donen
         *     `recent_consumptions` alanini yok saymak) gereksiz ag trafigi uretiyordu.
         *     Son tuketim satirlari baslik/tur tasir (MediaRecentConsumptionOut).
         */
        MediaDashboardOut: {
            /** Continue Items */
            continue_items: components["schemas"]["MediaItemOut"][];
            /** Recent Consumptions */
            recent_consumptions: components["schemas"]["MediaRecentConsumptionOut"][];
            stats: components["schemas"]["MediaStats"];
            /** Upcoming */
            upcoming: components["schemas"]["MediaUnitOut"][];
        };
        /** MediaDetailOut */
        MediaDetailOut: {
            /** Collections */
            collections: components["schemas"]["MediaCollectionOut"][];
            /**
             * Consumption Count
             * @default 0
             */
            consumption_count: number;
            /** Consumptions */
            consumptions: components["schemas"]["MediaConsumptionOut"][];
            /** Cycles */
            cycles: components["schemas"]["MediaCycleOut"][];
            item: components["schemas"]["MediaItemOut"];
            sync?: components["schemas"]["MediaItemSyncOut"] | null;
            /** Units */
            units: components["schemas"]["MediaUnitOut"][];
        };
        /** MediaItemIn */
        MediaItemIn: {
            /** Backdrop Path */
            backdrop_path?: string | null;
            /** Backdrop Url */
            backdrop_url?: string | null;
            /** Cover Path */
            cover_path?: string | null;
            /** Cover Url */
            cover_url?: string | null;
            /**
             * Favorite
             * @default false
             */
            favorite: boolean;
            /** Finished At */
            finished_at?: string | null;
            /** Kind */
            kind: string;
            /** Last Synced At */
            last_synced_at?: string | null;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            };
            /**
             * Monitored
             * @default false
             */
            monitored: boolean;
            /** Notes */
            notes?: string | null;
            /**
             * Owned
             * @default false
             */
            owned: boolean;
            /** Ownership */
            ownership?: {
                [key: string]: unknown;
            };
            /** Progress */
            progress?: number | null;
            /** Progress Measure */
            progress_measure?: string | null;
            /** Provider */
            provider?: string | null;
            /** Provider Id */
            provider_id?: string | null;
            /** Provider Ids */
            provider_ids?: {
                [key: string]: unknown;
            };
            /** Release Date */
            release_date?: string | null;
            /** Review */
            review?: string | null;
            /** Score */
            score?: number | null;
            /**
             * Source
             * @default manual
             * @enum {string}
             */
            source: "manual" | "provider";
            /** Started At */
            started_at?: string | null;
            /**
             * Status
             * @default planned
             */
            status: string;
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
            /** Total */
            total?: number | null;
        };
        /** MediaItemOut */
        MediaItemOut: {
            /** Archived At */
            archived_at?: string | null;
            /** Backdrop Path */
            backdrop_path?: string | null;
            /** Backdrop Url */
            backdrop_url?: string | null;
            /** Cover Path */
            cover_path?: string | null;
            /** Cover Url */
            cover_url?: string | null;
            /** Created At */
            created_at?: string | null;
            /**
             * Favorite
             * @default false
             */
            favorite: boolean;
            /** Finished At */
            finished_at?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Last Synced At */
            last_synced_at?: string | null;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            };
            /**
             * Monitored
             * @default false
             */
            monitored: boolean;
            /** Notes */
            notes?: string | null;
            /**
             * Owned
             * @default false
             */
            owned: boolean;
            /** Ownership */
            ownership?: {
                [key: string]: unknown;
            };
            /** Progress */
            progress?: number | null;
            /** Progress Measure */
            progress_measure?: string | null;
            /** Provider */
            provider?: string | null;
            /** Provider Id */
            provider_id?: string | null;
            /** Provider Ids */
            provider_ids?: {
                [key: string]: unknown;
            };
            /** Release Date */
            release_date?: string | null;
            /** Review */
            review?: string | null;
            /** Score */
            score?: number | null;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
            /** Total */
            total?: number | null;
            /** Updated At */
            updated_at?: string | null;
        };
        /**
         * MediaItemSyncOut
         * @description Tek kayit icin son senkron durumu (source_run turevi).
         */
        MediaItemSyncOut: {
            /** Items Found */
            items_found?: number | null;
            /** Last Error */
            last_error?: string | null;
            /** Last Run At */
            last_run_at?: string | null;
            /** Status */
            status: string;
        };
        /** MediaItemUpdate */
        MediaItemUpdate: {
            /** Backdrop Path */
            backdrop_path?: string | null;
            /** Backdrop Url */
            backdrop_url?: string | null;
            /** Cover Path */
            cover_path?: string | null;
            /** Cover Url */
            cover_url?: string | null;
            /** Favorite */
            favorite?: boolean | null;
            /** Finished At */
            finished_at?: string | null;
            /** Kind */
            kind?: string | null;
            /** Last Synced At */
            last_synced_at?: string | null;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            } | null;
            /** Monitored */
            monitored?: boolean | null;
            /** Notes */
            notes?: string | null;
            /** Owned */
            owned?: boolean | null;
            /** Ownership */
            ownership?: {
                [key: string]: unknown;
            } | null;
            /** Progress */
            progress?: number | null;
            /** Progress Measure */
            progress_measure?: string | null;
            /** Provider */
            provider?: string | null;
            /** Provider Id */
            provider_id?: string | null;
            /** Provider Ids */
            provider_ids?: {
                [key: string]: unknown;
            } | null;
            /** Release Date */
            release_date?: string | null;
            /** Review */
            review?: string | null;
            /** Score */
            score?: number | null;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status?: string | null;
            /** Summary */
            summary?: string | null;
            /** Title */
            title?: string | null;
            /** Total */
            total?: number | null;
        };
        /** MediaPageOut */
        MediaPageOut: {
            /** Items */
            items: components["schemas"]["MediaItemOut"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /** Total */
            total: number;
        };
        /** MediaProviderCapabilitiesOut */
        MediaProviderCapabilitiesOut: {
            /** Cache Artwork */
            cache_artwork: boolean;
            /** Details */
            details: boolean;
            /** Requires Settings */
            requires_settings: string[];
            /** Search */
            search: boolean;
            /** Units */
            units: boolean;
            /** Upcoming */
            upcoming: boolean;
        };
        /** MediaProviderStatusOut */
        MediaProviderStatusOut: {
            capabilities: components["schemas"]["MediaProviderCapabilitiesOut"];
            /** Id */
            id: string;
            /** Kinds */
            kinds: string[];
            /** Last Error */
            last_error?: string | null;
            /** Last Items Found */
            last_items_found?: number | null;
            /** Last Run At */
            last_run_at?: string | null;
            /** Last Status */
            last_status?: string | null;
            /** Missing Settings */
            missing_settings: string[];
            /** Ready */
            ready: boolean;
            /**
             * State
             * @default never_run
             * @enum {string}
             */
            state: "ready" | "missing_settings" | "never_run" | "running" | "ok" | "empty" | "error";
        };
        /**
         * MediaRecentConsumptionOut
         * @description Global son tüketim listesi satırı: medya başlığı ve türüyle birlikte.
         */
        MediaRecentConsumptionOut: {
            /** Action */
            action: string;
            /** Amount */
            amount?: number | null;
            /** Duration Min */
            duration_min?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Measure */
            measure?: string | null;
            /**
             * Media Id
             * Format: uuid
             */
            media_id: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Progress After */
            progress_after?: number | null;
            /** Title */
            title: string;
        };
        /** MediaStats */
        MediaStats: {
            /**
             * Active Days
             * @default 0
             */
            active_days: number;
            /** Average Score */
            average_score?: number | null;
            busiest_day?: components["schemas"]["MediaBusiestDayOut"] | null;
            /** By Kind */
            by_kind: {
                [key: string]: number;
            };
            /** By Measure */
            by_measure?: {
                [key: string]: number;
            };
            /** Completed */
            completed: number;
            /**
             * Completed In Range
             * @default 0
             */
            completed_in_range: number;
            conversion?: components["schemas"]["MediaConversionOut"];
            /** In Progress */
            in_progress: number;
            /** Planned */
            planned: number;
            /**
             * Pomodoro Minutes
             * @default 0
             */
            pomodoro_minutes: number;
            /** Score Distribution */
            score_distribution?: {
                [key: string]: number;
            };
            /**
             * Scored Count
             * @default 0
             */
            scored_count: number;
            /** Total */
            total: number;
            /**
             * Total Duration Min
             * @default 0
             */
            total_duration_min: number;
        };
        /** MediaSyncBatchOut */
        MediaSyncBatchOut: {
            /** Completed Sources */
            completed_sources: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Empty Sources */
            empty_sources: number;
            /** Error Sources */
            error_sources: number;
            /** Finished At */
            finished_at?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Items Found */
            items_found: number;
            /** Ok Sources */
            ok_sources: number;
            /** Progress Pct */
            progress_pct: number;
            /**
             * Scope
             * @constant
             */
            scope: "media";
            /** Source Ids */
            source_ids: string[];
            /** Started At */
            started_at?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "completed" | "completed_with_errors";
            /** Total Sources */
            total_sources: number;
        };
        /** MediaSyncIdleOut */
        MediaSyncIdleOut: {
            /**
             * Scope
             * @constant
             */
            scope: "media";
            /** Source Ids */
            source_ids: string[];
            /**
             * Status
             * @constant
             */
            status: "idle";
            /**
             * Total Sources
             * @constant
             */
            total_sources: 0;
        };
        /** MediaUnitOut */
        MediaUnitOut: {
            /** Children */
            children?: components["schemas"]["MediaUnitOut"][];
            /** Cover Path */
            cover_path?: string | null;
            /** Cover Url */
            cover_url?: string | null;
            /** Created At */
            created_at?: string | null;
            /** Duration Min */
            duration_min?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Media Id
             * Format: uuid
             */
            media_id: string;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            };
            /** Number */
            number?: number | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Progress Measure */
            progress_measure?: string | null;
            /** Progress Total */
            progress_total?: number | null;
            /** Provider */
            provider?: string | null;
            /** Provider Id */
            provider_id?: string | null;
            /** Provider Ids */
            provider_ids?: {
                [key: string]: unknown;
            };
            /** Release At */
            release_at?: string | null;
            /** Title */
            title: string;
            /** Unit Type */
            unit_type: string;
            /** Updated At */
            updated_at?: string | null;
        };
        /**
         * MediaUpcomingOut
         * @description Yaklasan yayin satiri: item yayin tarihi veya unit (bolum/parca) tarihi.
         */
        MediaUpcomingOut: {
            /** Cover Url */
            cover_url?: string | null;
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /**
             * Entry Type
             * @enum {string}
             */
            entry_type: "item" | "unit";
            /** Kind */
            kind: string;
            /**
             * Media Id
             * Format: uuid
             */
            media_id: string;
            /** Media Title */
            media_title: string;
            /**
             * Monitored
             * @default false
             */
            monitored: boolean;
            /** Number */
            number?: number | null;
            /** Provider */
            provider?: string | null;
            /**
             * Release At
             * Format: date-time
             */
            release_at: string;
            /** Title */
            title: string;
            /** Unit Type */
            unit_type?: string | null;
        };
        /** MediaUpcomingPageOut */
        MediaUpcomingPageOut: {
            /** Entries */
            entries: components["schemas"]["MediaUpcomingOut"][];
            /** Total */
            total: number;
        };
        /**
         * MetadataResult
         * @description Provider arama sonucunun ortak, kayda dönüştürülebilir biçimi.
         */
        MetadataResult: {
            /** Backdrop */
            backdrop?: string | null;
            /** Backdrop Url */
            backdrop_url?: string | null;
            /** Cover */
            cover?: string | null;
            /** Cover Url */
            cover_url?: string | null;
            /** Kind */
            kind: string;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            };
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Progress Measure */
            progress_measure?: string | null;
            /** Provider */
            provider: string;
            /** Provider Id */
            provider_id: string;
            /** Provider Ids */
            provider_ids?: {
                [key: string]: unknown;
            };
            /** Subtitle */
            subtitle?: string | null;
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
            /** Total */
            total?: number | null;
            /** Year */
            year?: number | null;
        };
        /** MetadataSearchWarning */
        MetadataSearchWarning: {
            /** Kind */
            kind: string;
            /** Message */
            message: string;
            /** Provider */
            provider: string;
        };
        /** MilestoneIn */
        MilestoneIn: {
            /** Due At */
            due_at?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
        };
        /** MilestonePatch */
        MilestonePatch: {
            /** Completed */
            completed?: boolean | null;
            /** Due At */
            due_at?: string | null;
            /** Position */
            position?: number | null;
            /** Title */
            title?: string | null;
        };
        /** MonthlyPoint */
        MonthlyPoint: {
            /**
             * Applications
             * @default 0
             */
            applications: number;
            /** Bookmarks */
            bookmarks: number;
            /** Month */
            month: string;
            /** Notes */
            notes: number;
            /** Pomodoros */
            pomodoros: number;
            /** Reviews */
            reviews: number;
            /** Rss Read */
            rss_read: number;
            /** Todos */
            todos: number;
        };
        /** NoteAttachmentOut */
        NoteAttachmentOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Mime */
            mime: string;
            /** Name */
            name: string;
            /** Size */
            size: number;
            /** Url */
            url: string;
        };
        /** NoteFolderIn */
        NoteFolderIn: {
            /** Name */
            name: string;
            /** Parent Id */
            parent_id?: string | null;
        };
        /** NoteFolderOut */
        NoteFolderOut: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /**
             * Note Count
             * @default 0
             */
            note_count: number;
            /** Parent Id */
            parent_id?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** NoteFolderUpdate */
        NoteFolderUpdate: {
            /** Name */
            name?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Position */
            position?: number | null;
        };
        /** NoteIn */
        NoteIn: {
            /** Body */
            body: string;
            /** Canvas State */
            canvas_state?: {
                [key: string]: unknown;
            };
            /**
             * Default View
             * @default page
             * @enum {string}
             */
            default_view: "page" | "canvas";
            /** Folder Id */
            folder_id?: string | null;
            /**
             * Page Width
             * @default compact
             * @enum {string}
             */
            page_width: "compact" | "wide" | "full";
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /** Relate To */
            relate_to?: string | null;
            /** Tags */
            tags?: string[];
        };
        /** NoteOut */
        NoteOut: {
            /** Attachments */
            attachments?: components["schemas"]["NoteAttachmentOut"][];
            /** Body */
            body: string;
            /** Canvas State */
            canvas_state?: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Default View
             * @default page
             * @enum {string}
             */
            default_view: "page" | "canvas";
            /** Folder Id */
            folder_id?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Journal Day */
            journal_day?: string | null;
            /**
             * Page Width
             * @default compact
             * @enum {string}
             */
            page_width: "compact" | "wide" | "full";
            /** Pinned */
            pinned: boolean;
            /** Project Id */
            project_id?: string | null;
            /** Resolved Links */
            resolved_links?: components["schemas"]["ResolvedLink"][];
            /** Tags */
            tags?: string[];
            /** Title */
            title: string;
            /** Unresolved Links */
            unresolved_links?: string[];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** NoteUpdate */
        NoteUpdate: {
            /** Body */
            body?: string | null;
            /** Canvas State */
            canvas_state?: {
                [key: string]: unknown;
            } | null;
            /** Default View */
            default_view?: ("page" | "canvas") | null;
            /** Folder Id */
            folder_id?: string | null;
            /** Page Width */
            page_width?: ("compact" | "wide" | "full") | null;
            /** Pinned */
            pinned?: boolean | null;
            /** Tags */
            tags?: string[] | null;
        };
        /** NotificationOut */
        NotificationOut: {
            /** Body */
            body: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Entity Id */
            entity_id: string | null;
            /** Entity Type */
            entity_type?: string | null;
            /** Id */
            id: number;
            /** Importance */
            importance: number;
            /** Kind */
            kind: string;
            /** Read At */
            read_at: string | null;
            /** Title */
            title: string;
        };
        /** OpenTodoOut */
        OpenTodoOut: {
            /** Due At */
            due_at?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Plan Day */
            plan_day?: string | null;
            /** Priority */
            priority?: number | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** OpportunityBrowseOut */
        OpportunityBrowseOut: {
            /** Facets */
            facets: {
                [key: string]: {
                    [key: string]: number;
                };
            };
            /** Items */
            items: components["schemas"]["OpportunityOut"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Section Counts */
            section_counts: {
                [key: string]: number;
            };
            /** Total */
            total: number;
        };
        /** OpportunityConnectionsOut */
        OpportunityConnectionsOut: {
            /** Connections */
            connections?: components["schemas"]["CareerConnectionOut"][];
            /** Normalized Organization */
            normalized_organization?: string | null;
            /** Organization */
            organization?: string | null;
        };
        /** OpportunityEvaluationOut */
        OpportunityEvaluationOut: {
            /** Archetype */
            archetype?: ("fde" | "sa" | "pm" | "llmops" | "agentic" | "transformation") | null;
            /** Archetype Scores */
            archetype_scores?: {
                [key: string]: number;
            };
            /** Candidate Document Id */
            candidate_document_id?: string | null;
            /** Candidate Document Title */
            candidate_document_title?: string | null;
            /**
             * Candidate Source
             * @default profile
             * @enum {string}
             */
            candidate_source: "document" | "profile";
            /**
             * Engine
             * @default local_rules
             * @constant
             */
            engine: "local_rules";
            /**
             * Evaluated At
             * Format: date-time
             */
            evaluated_at: string;
            gate: components["schemas"]["EvaluationGateOut"];
            /** Matches */
            matches?: components["schemas"]["EvaluationMatchOut"][];
            /** Notes */
            notes?: string | null;
            /**
             * Recommendation
             * @enum {string}
             */
            recommendation: "pursue" | "consider" | "skip";
            /** Requirements */
            requirements?: components["schemas"]["EvaluationRequirementOut"][];
            /** Score */
            score: number;
            /** Source Fingerprint */
            source_fingerprint: string;
            /** Version */
            version: string;
        };
        /** OpportunityEvaluationPatch */
        OpportunityEvaluationPatch: {
            /** Archetype */
            archetype?: ("fde" | "sa" | "pm" | "llmops" | "agentic" | "transformation") | null;
            /** Matches */
            matches?: components["schemas"]["EvaluationMatchOut"][] | null;
            /** Notes */
            notes?: string | null;
            /** Requirements */
            requirements?: components["schemas"]["EvaluationRequirementOut"][] | null;
        };
        /** OpportunityIn */
        OpportunityIn: {
            /** Compensation */
            compensation?: string | null;
            /** Deadline At */
            deadline_at?: string | null;
            /**
             * Kind
             * @default job
             */
            kind: string;
            /** Location */
            location?: string | null;
            /** Notes */
            notes?: string | null;
            /** Organization */
            organization?: string | null;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Remote */
            remote?: string | null;
            /**
             * Status
             * @default discovered
             */
            status: string;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** OpportunityIntelligenceOut */
        OpportunityIntelligenceOut: {
            /**
             * Connection Count
             * @default 0
             */
            connection_count: number;
            /**
             * Geo Mismatch
             * @default false
             */
            geo_mismatch: boolean;
            /**
             * Is Repost
             * @default false
             */
            is_repost: boolean;
            /** Pay Currency */
            pay_currency?: string | null;
            /** Pay Max */
            pay_max?: number | null;
            /** Pay Min */
            pay_min?: number | null;
            /** Pay Range Ratio */
            pay_range_ratio?: number | null;
            /**
             * Pay Transparency Risk
             * @default false
             */
            pay_transparency_risk: boolean;
            /**
             * Repost Count
             * @default 0
             */
            repost_count: number;
            /** Signals */
            signals?: components["schemas"]["RiskSignalOut"][];
            /**
             * Sponsorship Status
             * @default unstated
             * @enum {string}
             */
            sponsorship_status: "sponsors" | "not_needed" | "unstated" | "no_sponsorship";
        };
        /** OpportunityOut */
        OpportunityOut: {
            /** Allowed Application Transitions */
            allowed_application_transitions?: string[];
            /** Allowed Transitions */
            allowed_transitions?: string[];
            /** Application End At */
            application_end_at?: string | null;
            /** Application Start At */
            application_start_at?: string | null;
            /** Application Status */
            application_status?: string | null;
            /** Application Status Changed At */
            application_status_changed_at?: string | null;
            /** Applied At */
            applied_at: string | null;
            /** Apply Url */
            apply_url?: string | null;
            /** Category */
            category: string | null;
            /** Closed At */
            closed_at?: string | null;
            /** Compensation */
            compensation: string | null;
            /** Country */
            country?: string | null;
            /** Cv Document Id */
            cv_document_id?: string | null;
            /** Deadline At */
            deadline_at: string | null;
            evaluation?: components["schemas"]["OpportunityEvaluationOut"] | null;
            /** Exam At */
            exam_at?: string | null;
            /** External Id */
            external_id: string | null;
            /** Fields */
            fields?: string[];
            /** Follow Up At */
            follow_up_at?: string | null;
            /**
             * Found At
             * Format: date-time
             */
            found_at: string;
            /** Guide Url */
            guide_url?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            intelligence?: components["schemas"]["OpportunityIntelligenceOut"] | null;
            /** Kind */
            kind: string;
            /** Last Seen At */
            last_seen_at?: string | null;
            /** Location */
            location: string | null;
            /** Notes */
            notes: string | null;
            /** Official */
            official?: boolean | null;
            /** Organization */
            organization: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Priority */
            priority: number;
            /** Profile Match Ratio */
            profile_match_ratio?: number | null;
            /** Published At */
            published_at: string | null;
            /** Quota Total */
            quota_total?: number | null;
            /** Raw */
            raw: {
                [key: string]: unknown;
            };
            /** Region */
            region?: string | null;
            /** Rejection Reason */
            rejection_reason?: string | null;
            /** Remote */
            remote: string | null;
            /** Requirement Document Id */
            requirement_document_id?: string | null;
            /** Result At */
            result_at?: string | null;
            /** Score */
            score?: number | null;
            /** Score Computed At */
            score_computed_at?: string | null;
            /** Score Reasons */
            score_reasons?: {
                [key: string]: unknown;
            } | null;
            /** Score Source */
            score_source?: string | null;
            skill_match?: components["schemas"]["SkillMatchOut"] | null;
            /** Source */
            source: string;
            /**
             * Source Status
             * @default active
             */
            source_status: string;
            /** Stage */
            stage?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
            /** Trashed At */
            trashed_at?: string | null;
            /** Trashed From Status */
            trashed_from_status?: string | null;
            /** Url */
            url: string | null;
        };
        /** OpportunityPatch */
        OpportunityPatch: {
            /** Deadline At */
            deadline_at?: string | null;
            /** Follow Up At */
            follow_up_at?: string | null;
            /** Notes */
            notes?: string | null;
            /** Priority */
            priority?: number | null;
            /** Rejection Reason */
            rejection_reason?: string | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
        };
        /**
         * OpportunityUsageOut
         * @description Bir fırsatın belgeyle bağı (cv: başvuru kaydındaki CV, requirement: gereksinim belgesi).
         */
        OpportunityUsageOut: {
            /** Kind */
            kind: string;
            /**
             * Opportunity Id
             * Format: uuid
             */
            opportunity_id: string;
            /**
             * Relation
             * @enum {string}
             */
            relation: "cv" | "requirement";
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** PlanSlotIn */
        PlanSlotIn: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Duration Min */
            duration_min?: number | null;
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /** Note */
            note?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Start Min */
            start_min?: number | null;
        };
        /** PlanSlotOut */
        PlanSlotOut: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Duration Min */
            duration_min: number | null;
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /** Entity Type */
            entity_type: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Note */
            note: string | null;
            /** Position */
            position: number;
            /** Start Min */
            start_min: number | null;
            /** Title */
            title: string;
        };
        /** PlanSlotUpdate */
        PlanSlotUpdate: {
            /** Day */
            day?: string | null;
            /** Duration Min */
            duration_min?: number | null;
            /** Note */
            note?: string | null;
            /** Position */
            position?: number | null;
            /** Start Min */
            start_min?: number | null;
        };
        /**
         * PomodoroManual
         * @description Gecmise elle islenen seans -- sayac calistirilmadan yapilan is.
         */
        PomodoroManual: {
            /** Context Entity Id */
            context_entity_id?: string | null;
            /**
             * Kind
             * @default focus
             */
            kind: string;
            /** Minutes */
            minutes: number;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Topic */
            topic?: string | null;
        };
        /** PomodoroOut */
        PomodoroOut: {
            /** Actual Min */
            actual_min: number | null;
            /** Context Entity Id */
            context_entity_id: string | null;
            /** Context Title */
            context_title?: string | null;
            /** Context Type */
            context_type?: string | null;
            /** Ended At */
            ended_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Interrupted */
            interrupted: boolean;
            /** Kind */
            kind: string;
            /** Paused At */
            paused_at?: string | null;
            /**
             * Paused S
             * @default 0
             */
            paused_s: number;
            /** Planned Min */
            planned_min: number;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Topic */
            topic: string | null;
        };
        /** PomodoroStart */
        PomodoroStart: {
            /** Context Entity Id */
            context_entity_id?: string | null;
            /**
             * Kind
             * @default focus
             */
            kind: string;
            /**
             * Planned Min
             * @default 50
             */
            planned_min: number;
            /** Topic */
            topic?: string | null;
        };
        /** PomodoroStats */
        PomodoroStats: {
            /** Interrupted */
            interrupted: number;
            /** Minutes */
            minutes: number;
            /** Sessions */
            sessions: number;
        };
        /** PomodoroStop */
        PomodoroStop: {
            /**
             * Interrupted
             * @default false
             */
            interrupted: boolean;
        };
        /** ProjectIn */
        ProjectIn: {
            /** Github Repo */
            github_repo?: string | null;
            /** Next Action */
            next_action?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Stack
             * @default []
             */
            stack: string[];
            /**
             * Status
             * @default active
             */
            status: string;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** ProjectJournalNoteIn */
        ProjectJournalNoteIn: {
            /** Body */
            body: string;
        };
        /** ProjectPatch */
        ProjectPatch: {
            /** Github Repo */
            github_repo?: string | null;
            /** Next Action */
            next_action?: string | null;
            /** Position */
            position?: number | null;
            /** Stack */
            stack?: string[] | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
            /** Url */
            url?: string | null;
        };
        /**
         * PrunePreviewOut
         * @description Silme onizlemesi. Kullaniciya ikinci onaydan once gosterilir.
         */
        PrunePreviewOut: {
            /** Archived */
            archived: number;
            /** Candidates */
            candidates: number;
            /** Confirm Token */
            confirm_token: string;
            /** Days */
            days: number;
            /** Estimated Bytes */
            estimated_bytes: number;
            /** Protected */
            protected: number;
        };
        /** PruneResultOut */
        PruneResultOut: {
            /** Archived */
            archived: number;
            /** Days */
            days: number;
            /**
             * Event
             * @default opportunity.pruned
             */
            event: string;
            /** Freed Bytes */
            freed_bytes: number;
            /** Protected */
            protected: number;
            /** Pruned */
            pruned: number;
        };
        /** RecurringIn */
        RecurringIn: {
            /**
             * Active
             * @default true
             */
            active: boolean;
            /** Amount */
            amount: number | string;
            /** Billing Day */
            billing_day?: number | null;
            /**
             * Category
             * @default subscriptions
             */
            category: string;
            /**
             * Currency
             * @default TRY
             */
            currency: string;
            /**
             * Frequency
             * @default monthly
             */
            frequency: string;
            /** Next Due At */
            next_due_at?: string | null;
            /** Note */
            note?: string | null;
            /** Sub */
            sub?: string | null;
            /** Title */
            title: string;
        };
        /** RecurringPatch */
        RecurringPatch: {
            /** Active */
            active?: boolean | null;
            /** Amount */
            amount?: number | string | null;
            /** Billing Day */
            billing_day?: number | null;
            /** Category */
            category?: string | null;
            /** Currency */
            currency?: string | null;
            /** Frequency */
            frequency?: string | null;
            /** Next Due At */
            next_due_at?: string | null;
            /** Note */
            note?: string | null;
            /** Sub */
            sub?: string | null;
            /** Title */
            title?: string | null;
        };
        /**
         * RelatedOut
         * @description GET /entities/{id}/related satiri: iliski + yon + karsi entity ozeti.
         */
        RelatedOut: {
            /** Direction */
            direction: string;
            entity: components["schemas"]["EntityOut"];
            /** Label */
            label: string;
            /** Relation */
            relation: string;
        };
        /** ReplyAnalysisIn */
        ReplyAnalysisIn: {
            /** Text */
            text: string;
        };
        /** ReplyAnalysisOut */
        ReplyAnalysisOut: {
            /** Confidence */
            confidence: number;
            /** Evidence */
            evidence: string[];
            /**
             * Kind
             * @enum {string}
             */
            kind: "interview_invite" | "rejection" | "take_home_assessment" | "auto_acknowledgement" | "unknown";
            /** Label */
            label: string;
            /** Suggested Status */
            suggested_status?: ("applied" | "interview" | "rejected") | null;
            /** Suggested Todo Title */
            suggested_todo_title?: string | null;
            /** Summary */
            summary: string;
        };
        /** RequirementDocumentIn */
        RequirementDocumentIn: {
            /** Document Entity Id */
            document_entity_id: string | null;
        };
        /** RequirementIn */
        RequirementIn: {
            /** Name */
            name: string;
            /** Note */
            note?: string | null;
            /**
             * Required
             * @default true
             */
            required: boolean;
            /**
             * Status
             * @default missing
             * @enum {string}
             */
            status: "missing" | "ready" | "submitted" | "waived";
        };
        /** RequirementOut */
        RequirementOut: {
            /** Document Entity Id */
            document_entity_id?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Note */
            note?: string | null;
            /**
             * Opportunity Id
             * Format: uuid
             */
            opportunity_id: string;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Required
             * @default true
             */
            required: boolean;
            /**
             * Status
             * @default missing
             * @enum {string}
             */
            status: "missing" | "ready" | "submitted" | "waived";
        };
        /**
         * ResolvedLink
         * @description Govdedeki [[hedef]] -> gercek kayit.
         */
        ResolvedLink: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Target */
            target: string;
            /** Type */
            type: string;
        };
        /** ResourceIn */
        ResourceIn: {
            /** Estimated Min */
            estimated_min?: number | null;
            /**
             * Kind
             * @default link
             */
            kind: string;
            /** Note */
            note?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** ResourceOut */
        ResourceOut: {
            /** Bookmark Id */
            bookmark_id?: string | null;
            /** Completed At */
            completed_at?: string | null;
            /** Course Id */
            course_id?: string | null;
            /** Estimated Min */
            estimated_min?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @default link
             */
            kind: string;
            /** Last Opened At */
            last_opened_at?: string | null;
            /** Note */
            note?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Source
             * @default manual
             */
            source: string;
            /** Title */
            title: string;
            /**
             * Topic Id
             * Format: uuid
             */
            topic_id: string;
            /** Url */
            url?: string | null;
        };
        /** ResourcePatch */
        ResourcePatch: {
            /** Completed */
            completed?: boolean | null;
            /** Estimated Min */
            estimated_min?: number | null;
            /** Kind */
            kind?: string | null;
            /** Note */
            note?: string | null;
            /** Position */
            position?: number | null;
            /** Title */
            title?: string | null;
            /** Url */
            url?: string | null;
        };
        /** ResourceSeed */
        ResourceSeed: {
            /** Estimated Min */
            estimated_min?: number | null;
            /**
             * Kind
             * @default link
             */
            kind: string;
            /** Note */
            note?: string | null;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** ReviewBlockOut */
        ReviewBlockOut: {
            /**
             * Due
             * @default false
             */
            due: boolean;
            /**
             * Ease
             * @default 2.5
             */
            ease: number;
            /**
             * Interval Days
             * @default 0
             */
            interval_days: number;
            /** Last Reviewed At */
            last_reviewed_at?: string | null;
            /** Mastery */
            mastery?: number | null;
            /** Next Review At */
            next_review_at?: string | null;
            /**
             * Review Count
             * @default 0
             */
            review_count: number;
        };
        /** ReviewPreview */
        ReviewPreview: {
            /** Completed Todos */
            completed_todos: components["schemas"]["CompletedTodo"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "daily" | "weekly";
            /**
             * Period End
             * Format: date
             */
            period_end: string;
            /**
             * Period Start
             * Format: date
             */
            period_start: string;
            stats: components["schemas"]["ReviewStats"];
            /** Unfinished Todos */
            unfinished_todos: components["schemas"]["UnfinishedTodo"][];
        };
        /** ReviewQueueOut */
        ReviewQueueOut: {
            /** Due Today */
            due_today?: components["schemas"]["ReviewTopicOut"][];
            /** New Topics */
            new_topics?: components["schemas"]["ReviewTopicOut"][];
            /** Overdue */
            overdue?: components["schemas"]["ReviewTopicOut"][];
            /** Upcoming */
            upcoming?: components["schemas"]["ReviewTopicOut"][];
            /** Weak */
            weak?: components["schemas"]["ReviewTopicOut"][];
        };
        /** ReviewStats */
        ReviewStats: {
            applications: components["schemas"]["ApplicationReviewStats"];
            capture: components["schemas"]["CaptureReviewStats"];
            flashcards: components["schemas"]["FlashcardReviewStats"];
            focus: components["schemas"]["FocusReviewStats"];
            github: components["schemas"]["GithubReviewStats"];
            /** Habits */
            habits: {
                [key: string]: number;
            };
            study: components["schemas"]["StudyReviewStats"];
            todos: components["schemas"]["TodoReviewStats"];
            /** Topics */
            topics: components["schemas"]["TopicReviewStats"][];
        };
        /** ReviewTopicOut */
        ReviewTopicOut: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /** Area Title */
            area_title: string;
            /** Confidence */
            confidence?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Interval Days
             * @default 0
             */
            interval_days: number;
            /** Last Reviewed At */
            last_reviewed_at?: string | null;
            /** Last Studied At */
            last_studied_at?: string | null;
            /** Mastery */
            mastery?: number | null;
            /** Next Review At */
            next_review_at?: string | null;
            /**
             * Review Count
             * @default 0
             */
            review_count: number;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** RiskSignalOut */
        RiskSignalOut: {
            /** Code */
            code: string;
            /** Detail */
            detail: string;
            /** Label */
            label: string;
            /**
             * Severity
             * @default neutral
             * @enum {string}
             */
            severity: "neutral" | "warn" | "danger";
        };
        /** RssStats */
        RssStats: {
            /** Active Feeds */
            active_feeds: number;
            /** Failing Feeds */
            failing_feeds: number;
            /** Feeds */
            feeds: number;
            /**
             * Saved
             * @default 0
             */
            saved: number;
            /**
             * Today
             * @default 0
             */
            today: number;
            /** Unread */
            unread: number;
        };
        /** SalaryClaimOut */
        SalaryClaimOut: {
            /** Currency */
            currency?: string | null;
            /**
             * Interview Id
             * Format: uuid
             */
            interview_id: string;
            /** Pay Max */
            pay_max?: number | null;
            /** Pay Min */
            pay_min?: number | null;
            /** Stage */
            stage: string;
            /** Statement */
            statement: string;
        };
        /** SalaryConsistencyOut */
        SalaryConsistencyOut: {
            /** Claims */
            claims?: components["schemas"]["SalaryClaimOut"][];
            /**
             * Inconsistent
             * @default false
             */
            inconsistent: boolean;
            /** Warning */
            warning?: string | null;
        };
        /** SaveItemIn */
        SaveItemIn: {
            /**
             * Collection
             * @default read_later
             */
            collection: string;
        };
        /**
         * SavedViewCreate
         * @description POST /views govdesi: position sunucu tarafinda (max+1) hesaplanir.
         */
        SavedViewCreate: {
            /** Filter */
            filter: {
                [key: string]: unknown;
            };
            /** Module */
            module: string;
            /** Name */
            name: string;
            /** Sort */
            sort?: string | null;
        };
        /** SavedViewOut */
        SavedViewOut: {
            /**
             * Filter
             * @default {}
             */
            filter: {
                [key: string]: unknown;
            };
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Module */
            module: string;
            /** Name */
            name: string;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Sort */
            sort?: string | null;
        };
        /**
         * SavedViewPatch
         * @description PATCH /views/{id} govdesi: verilen alanlar guncellenir.
         */
        SavedViewPatch: {
            /** Filter */
            filter?: {
                [key: string]: unknown;
            } | null;
            /** Name */
            name?: string | null;
            /** Pinned */
            pinned?: boolean | null;
            /** Sort */
            sort?: string | null;
        };
        /** SettingIn */
        SettingIn: {
            /** Value */
            value: unknown;
        };
        /** SilentApplicationOut */
        SilentApplicationOut: {
            /** Days Silent */
            days_silent: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Last Interview At
             * Format: date-time
             */
            last_interview_at: string;
            /** Organization */
            organization?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** SkillMatchOut */
        SkillMatchOut: {
            /** Match Ratio */
            match_ratio: number;
            /** Matched */
            matched: string[];
            /** Missing */
            missing: string[];
        };
        /**
         * SourceRefreshIn
         * @description Bos govde = genel yenileme (critical + normal; opt-in HARIC).
         */
        SourceRefreshIn: {
            /** Kind */
            kind?: ("job" | "announcement") | null;
            /**
             * Mode
             * @default general
             * @enum {string}
             */
            mode: "critical" | "general" | "full";
            /** Source Ids */
            source_ids?: string[] | null;
        };
        /** SourceRefreshResult */
        SourceRefreshResult: {
            /** Batch Id */
            batch_id: string | null;
            /**
             * Estimated Seconds
             * @default 0
             */
            estimated_seconds: number;
            /**
             * Mode
             * @default general
             */
            mode: string;
            /** Queued */
            queued: number;
            /** Total Sources */
            total_sources: number;
        };
        /** SourceRunOut */
        SourceRunOut: {
            /** Error */
            error?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Items Found */
            items_found: number;
            /** Source */
            source: string;
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Status */
            status: string;
        };
        /** SourceSyncBatchOut */
        SourceSyncBatchOut: {
            /** Completed Sources */
            completed_sources: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Empty Sources */
            empty_sources: number;
            /** Error Sources */
            error_sources: number;
            /** Finished At */
            finished_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Items Found */
            items_found: number;
            /** Ok Sources */
            ok_sources: number;
            /** Progress Pct */
            progress_pct: number;
            /**
             * Scope
             * @default opportunity
             * @enum {string}
             */
            scope: "opportunity" | "media";
            /** Source Ids */
            source_ids: string[];
            /** Started At */
            started_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "completed" | "completed_with_errors";
            /** Total Sources */
            total_sources: number;
        };
        /** SourceSyncItemOut */
        SourceSyncItemOut: {
            /** Error */
            error: string | null;
            /** Finished At */
            finished_at: string | null;
            /** Items Found */
            items_found: number;
            /** Source */
            source: string;
            /** Started At */
            started_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "ok" | "empty" | "error";
        };
        /** SourceSyncStatusOut */
        SourceSyncStatusOut: {
            active: components["schemas"]["SourceSyncBatchOut"] | null;
            last_completed: components["schemas"]["SourceSyncBatchOut"] | null;
            /** Running */
            running: components["schemas"]["SourceSyncItemOut"][];
            /** Sources */
            sources: components["schemas"]["SourceSyncItemOut"][];
        };
        /** StalePageOut */
        StalePageOut: {
            /** Items */
            items?: components["schemas"]["StudyTopicOut"][];
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /**
         * StatisticsSummary
         * @description Keyfi verb ailesine gore sayaclar: family adi -> dilimler.
         */
        StatisticsSummary: {
            applications: components["schemas"]["CounterBreakdown"];
            /** Counters */
            counters: {
                [key: string]: components["schemas"]["CounterBreakdown"];
            };
            streak: components["schemas"]["StreakOut"];
        };
        /** StatsAreaOut */
        StatsAreaOut: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /**
             * Minutes
             * @default 0
             */
            minutes: number;
            /** Title */
            title: string;
        };
        /** StatsCourseOut */
        StatsCourseOut: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * In Progress
             * @default 0
             */
            in_progress: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** StatsTopicOut */
        StatsTopicOut: {
            /**
             * Minutes
             * @default 0
             */
            minutes: number;
            /** Title */
            title: string;
            /**
             * Topic Id
             * Format: uuid
             */
            topic_id: string;
        };
        /** StreakOut */
        StreakOut: {
            /** Current */
            current: number;
            /** Longest */
            longest: number;
        };
        /** StudyAreaOut */
        StudyAreaOut: {
            /**
             * Active
             * @default true
             */
            active: boolean;
            /** Archived At */
            archived_at?: string | null;
            /** Color */
            color?: string | null;
            /**
             * Done Count
             * @default 0
             */
            done_count: number;
            /**
             * Focus Minutes
             * @default 0
             */
            focus_minutes: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Studied At */
            last_studied_at?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Resource Count
             * @default 0
             */
            resource_count: number;
            /**
             * Resource Done
             * @default 0
             */
            resource_done: number;
            /**
             * Stale Count
             * @default 0
             */
            stale_count: number;
            /** Title */
            title: string;
            /**
             * Topic Count
             * @default 0
             */
            topic_count: number;
        };
        /** StudyReviewStats */
        StudyReviewStats: {
            /** Minutes By Area */
            minutes_by_area: {
                [key: string]: number;
            };
        };
        /** StudyStatsOut */
        StudyStatsOut: {
            /**
             * Active Days
             * @default 0
             */
            active_days: number;
            /**
             * Actual Minutes
             * @default 0
             */
            actual_minutes: number;
            /** By Area */
            by_area?: components["schemas"]["StatsAreaOut"][];
            /** By Topic */
            by_topic?: components["schemas"]["StatsTopicOut"][];
            /**
             * Confidence Delta
             * @default 0
             */
            confidence_delta: number;
            courses?: components["schemas"]["StatsCourseOut"];
            /**
             * Flashcards Reviewed
             * @default 0
             */
            flashcards_reviewed: number;
            /**
             * Focus Minutes
             * @default 0
             */
            focus_minutes: number;
            /**
             * Focus Sessions
             * @default 0
             */
            focus_sessions: number;
            /**
             * Planned Minutes
             * @default 0
             */
            planned_minutes: number;
            /**
             * Resources Done
             * @default 0
             */
            resources_done: number;
            /**
             * Reviews Done
             * @default 0
             */
            reviews_done: number;
            /**
             * Streak Days
             * @default 0
             */
            streak_days: number;
            /**
             * Topics Done
             * @default 0
             */
            topics_done: number;
            /**
             * Topics Started
             * @default 0
             */
            topics_started: number;
        };
        /** StudyTopicDetailOut */
        StudyTopicDetailOut: {
            /** Ancestors */
            ancestors?: components["schemas"]["AncestorOut"][];
            /**
             * Flashcard Deck Count
             * @default 0
             */
            flashcard_deck_count: number;
            /**
             * Note Count
             * @default 0
             */
            note_count: number;
            open_todo?: components["schemas"]["OpenTodoOut"] | null;
            progress: components["schemas"]["TopicProgressOut"];
            /** Resources */
            resources?: components["schemas"]["ResourceOut"][];
            review: components["schemas"]["ReviewBlockOut"];
            stats: components["schemas"]["TopicStatsDetailOut"];
            topic: components["schemas"]["StudyTopicOut"];
        };
        /**
         * StudyTopicLegacyNode
         * @description `GET /study/topics?area_id=` eski (ic ice) sekli -- yol korunur.
         */
        StudyTopicLegacyNode: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /** Children */
            children?: components["schemas"]["StudyTopicLegacyNode"][];
            /** Confidence */
            confidence?: number | null;
            /**
             * Ease
             * @default 2.5
             */
            ease: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Interval Days
             * @default 0
             */
            interval_days: number;
            /** Last Reviewed At */
            last_reviewed_at?: string | null;
            /** Last Studied At */
            last_studied_at?: string | null;
            /** Mastery */
            mastery?: number | null;
            /** Next Review At */
            next_review_at?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            progress?: components["schemas"]["TopicProgressOut"];
            /**
             * Review Count
             * @default 0
             */
            review_count: number;
            /** Status */
            status: string;
            /** Target Min */
            target_min?: number | null;
            /** Title */
            title: string;
        };
        /** StudyTopicNode */
        StudyTopicNode: {
            /**
             * Child Count
             * @default 0
             */
            child_count: number;
            /** Confidence */
            confidence?: number | null;
            /**
             * Depth
             * @default 0
             */
            depth: number;
            /**
             * Focus Minutes
             * @default 0
             */
            focus_minutes: number;
            /**
             * Focus Sessions
             * @default 0
             */
            focus_sessions: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Studied At */
            last_studied_at?: string | null;
            /** Mastery */
            mastery?: number | null;
            /** Next Review At */
            next_review_at?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Path */
            path?: string[];
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Progress Pct
             * @default 0
             */
            progress_pct: number;
            /**
             * Resource Done
             * @default 0
             */
            resource_done: number;
            /**
             * Resource Total
             * @default 0
             */
            resource_total: number;
            /** Resources */
            resources?: components["schemas"]["ResourceOut"][] | null;
            /**
             * Review Due
             * @default false
             */
            review_due: boolean;
            /** Status */
            status: string;
            /** Target Min */
            target_min?: number | null;
            /** Title */
            title: string;
        };
        /** StudyTopicOut */
        StudyTopicOut: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /** Confidence */
            confidence?: number | null;
            /**
             * Ease
             * @default 2.5
             */
            ease: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Interval Days
             * @default 0
             */
            interval_days: number;
            /** Last Reviewed At */
            last_reviewed_at?: string | null;
            /** Last Studied At */
            last_studied_at?: string | null;
            /** Mastery */
            mastery?: number | null;
            /** Next Review At */
            next_review_at?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Review Count
             * @default 0
             */
            review_count: number;
            /** Status */
            status: string;
            /** Target Min */
            target_min?: number | null;
            /** Title */
            title: string;
        };
        /** StudyTreeOut */
        StudyTreeOut: {
            area: components["schemas"]["StudyAreaOut"];
            /** Nodes */
            nodes?: components["schemas"]["StudyTopicNode"][];
            /**
             * Orphan Count
             * @default 0
             */
            orphan_count: number;
            totals: components["schemas"]["StudyTreeTotals"];
        };
        /** StudyTreeTotals */
        StudyTreeTotals: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * Focus Minutes
             * @default 0
             */
            focus_minutes: number;
            /**
             * Focus Sessions
             * @default 0
             */
            focus_sessions: number;
            /**
             * In Progress
             * @default 0
             */
            in_progress: number;
            /**
             * Resource Done
             * @default 0
             */
            resource_done: number;
            /**
             * Resource Total
             * @default 0
             */
            resource_total: number;
            /**
             * Review Due
             * @default 0
             */
            review_due: number;
            /**
             * Topics
             * @default 0
             */
            topics: number;
        };
        /** SyncIn */
        SyncIn: {
            /**
             * Category
             * @default other
             */
            category: string;
            /** Folder Id */
            folder_id: string;
        };
        /** TagOut */
        TagOut: {
            /** Count */
            count: number;
            /** Name */
            name: string;
        };
        /**
         * TimelineEntryOut
         * @description Basvuru zaman cizelgesi -- event/history kayitlarindan deterministik uretilir.
         */
        TimelineEntryOut: {
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Detail */
            detail?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "discovered" | "shortlisted" | "status" | "followup" | "interview" | "note" | "document" | "todo" | "offer" | "rejection";
            /** Status */
            status?: string | null;
            /** Title */
            title: string;
        };
        /** TodayAgendaOut */
        TodayAgendaOut: {
            /**
             * Auto Suggestions
             * @default true
             */
            auto_suggestions: boolean;
            /** Checklist */
            checklist?: components["schemas"]["AgendaRow"][];
            /** Completed */
            completed?: components["schemas"]["AgendaRow"][];
            /**
             * Day
             * Format: date
             */
            day: string;
            suggestions?: components["schemas"]["AgendaSuggestions"];
            /** Timed */
            timed?: components["schemas"]["AgendaRow"][];
        };
        /** TodoIn */
        TodoIn: {
            /** Description */
            description?: string | null;
            /** Due At */
            due_at?: string | null;
            /** Milestone Id */
            milestone_id?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Plan Day */
            plan_day?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Project Id */
            project_id?: string | null;
            /** Recur */
            recur?: ("daily" | "weekdays" | "weekly" | "monthly") | null;
            /** Reminder At */
            reminder_at?: string | null;
            /**
             * Status
             * @default open
             */
            status: string;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Title */
            title: string;
        };
        /** TodoLinkIn */
        TodoLinkIn: {
            /**
             * Todo Id
             * Format: uuid
             */
            todo_id: string;
        };
        /** TodoOut */
        TodoOut: {
            /** Completed At */
            completed_at: string | null;
            /** Description */
            description: string | null;
            /** Due At */
            due_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Learning Topic Id */
            learning_topic_id?: string | null;
            /** Learning Topic Title */
            learning_topic_title?: string | null;
            /** Milestone Id */
            milestone_id?: string | null;
            /** Milestone Title */
            milestone_title?: string | null;
            /** Parent Id */
            parent_id: string | null;
            /** Planned Day */
            planned_day?: string | null;
            /** Planned Start Min */
            planned_start_min?: number | null;
            /** Position */
            position: number;
            /** Priority */
            priority: number;
            /** Project Id */
            project_id?: string | null;
            /** Project Title */
            project_title?: string | null;
            /** Recur */
            recur?: string | null;
            /** Reminder At */
            reminder_at: string | null;
            /** Status */
            status: string;
            /**
             * Subtask Done
             * @default 0
             */
            subtask_done: number;
            /**
             * Subtask Total
             * @default 0
             */
            subtask_total: number;
            /**
             * Tags
             * @default []
             */
            tags: string[];
            /** Title */
            title: string;
        };
        /** TodoReviewStats */
        TodoReviewStats: {
            /** Completed */
            completed: number;
            /** Created */
            created: number;
            /** Dropped */
            dropped: number;
            /** Overdue Now */
            overdue_now: number;
        };
        /** TodoUpdate */
        TodoUpdate: {
            /** Description */
            description?: string | null;
            /** Due At */
            due_at?: string | null;
            /** Milestone Id */
            milestone_id?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Position */
            position?: number | null;
            /** Priority */
            priority?: number | null;
            /** Recur */
            recur?: ("daily" | "weekdays" | "weekly" | "monthly") | "" | null;
            /** Reminder At */
            reminder_at?: string | null;
            /** Status */
            status?: string | null;
            /** Tags */
            tags?: string[] | null;
            /** Title */
            title?: string | null;
        };
        /** TopicImpactOut */
        TopicImpactOut: {
            /**
             * Links
             * @default 0
             */
            links: number;
            /**
             * Notes
             * @default 0
             */
            notes: number;
            /**
             * Plan Slots
             * @default 0
             */
            plan_slots: number;
            /**
             * Resources
             * @default 0
             */
            resources: number;
            /**
             * Todos
             * @default 0
             */
            todos: number;
            /**
             * Topics
             * @default 0
             */
            topics: number;
        };
        /** TopicImportIn */
        TopicImportIn: {
            /** Area */
            area?: string | null;
            /** Area Id */
            area_id?: string | null;
            /**
             * Prune
             * @default false
             */
            prune: boolean;
            /**
             * Strip Common Prefix
             * @default false
             */
            strip_common_prefix: boolean;
            /** Topics */
            topics: components["schemas"]["TopicSeed"][];
            /**
             * Update Existing
             * @default true
             */
            update_existing: boolean;
        };
        /** TopicImportOut */
        TopicImportOut: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /** Area Title */
            area_title: string;
            /**
             * Resources Archived
             * @default 0
             */
            resources_archived: number;
            /** Resources Created */
            resources_created: number;
            /** Resources Skipped */
            resources_skipped: number;
            /**
             * Resources Updated
             * @default 0
             */
            resources_updated: number;
            /**
             * Topics Archived
             * @default 0
             */
            topics_archived: number;
            /** Topics Created */
            topics_created: number;
            /** Topics Matched */
            topics_matched: number;
            /**
             * Topics Updated
             * @default 0
             */
            topics_updated: number;
        };
        /** TopicIn */
        TopicIn: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /** Confidence */
            confidence?: number | null;
            /** Parent Id */
            parent_id?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Status
             * @default not_started
             */
            status: string;
            /** Target Min */
            target_min?: number | null;
            /** Title */
            title: string;
        };
        /** TopicMoveIn */
        TopicMoveIn: {
            /** Parent Id */
            parent_id?: string | null;
            /** Position */
            position?: number | null;
        };
        /** TopicPatch */
        TopicPatch: {
            /** Confidence */
            confidence?: number | null;
            /** Mastery */
            mastery?: number | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Position */
            position?: number | null;
            /** Status */
            status?: string | null;
            /** Target Min */
            target_min?: number | null;
            /** Title */
            title?: string | null;
        };
        /** TopicProgressOut */
        TopicProgressOut: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * Pct
             * @default 0
             */
            pct: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** TopicReviewIn */
        TopicReviewIn: {
            /**
             * Grade
             * @enum {string}
             */
            grade: "forgot" | "hard" | "medium" | "easy" | "very_easy";
            /** Mastery */
            mastery?: number | null;
        };
        /** TopicReviewOut */
        TopicReviewOut: {
            /**
             * Due
             * @default false
             */
            due: boolean;
            /**
             * Ease
             * @default 2.5
             */
            ease: number;
            /**
             * Interval Days
             * @default 0
             */
            interval_days: number;
            /** Last Reviewed At */
            last_reviewed_at?: string | null;
            /** Mastery */
            mastery?: number | null;
            /** Next Review At */
            next_review_at?: string | null;
            /**
             * Review Count
             * @default 0
             */
            review_count: number;
        };
        /** TopicReviewStats */
        TopicReviewStats: {
            /** Minutes */
            minutes: number;
            /** Topic */
            topic: string;
        };
        /** TopicSeed */
        TopicSeed: {
            /** Children */
            children?: components["schemas"]["TopicSeed"][];
            /** Position */
            position?: number | null;
            /** Resources */
            resources?: components["schemas"]["ResourceSeed"][];
            /**
             * Status
             * @default not_started
             */
            status: string;
            /** Target Min */
            target_min?: number | null;
            /** Title */
            title: string;
        };
        /** TopicStatsDetailOut */
        TopicStatsDetailOut: {
            /** Last Studied At */
            last_studied_at?: string | null;
            /**
             * Minutes
             * @default 0
             */
            minutes: number;
            /**
             * Sessions
             * @default 0
             */
            sessions: number;
            /**
             * Week Minutes
             * @default 0
             */
            week_minutes: number;
        };
        /**
         * TopicTodoIn
         * @description Konu gorevi icin ortak alan sozlesmesi (Faz 31).
         *
         *     Title/description konudan sabit kalir; plan_day/oncelik/tekrar/etiket
         *     gibi kullanici alanlari govdeden gelir -- "bugune al" tercihi plan_day
         *     olarak buradan uygulanir.
         */
        TopicTodoIn: {
            /** Due At */
            due_at?: string | null;
            /**
             * Force
             * @default false
             */
            force: boolean;
            /** Plan Day */
            plan_day?: string | null;
            /** Priority */
            priority?: number | null;
            /** Recur */
            recur?: string | null;
            /** Tags */
            tags?: string[];
        };
        /** TopicTodoOut */
        TopicTodoOut: {
            /** Created */
            created: boolean;
            todo: components["schemas"]["TodoOut"];
        };
        /** TransitionIn */
        TransitionIn: {
            /** Note */
            note?: string | null;
            /** Rejection Reason */
            rejection_reason?: string | null;
            /** To */
            to: string;
        };
        /** UnfinishedTodo */
        UnfinishedTodo: {
            /** Due At */
            due_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Priority */
            priority: number;
            /** Title */
            title: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** ReviewIn */
        app__modules__flashcard__schemas__ReviewIn: {
            /** Grade */
            grade: number;
        };
        /** ReviewOut */
        app__modules__flashcard__schemas__ReviewOut: {
            /**
             * Due At
             * Format: date-time
             */
            due_at: string;
            /** Interval Days */
            interval_days: number;
        };
        /** ReviewIn */
        app__modules__review__schemas__ReviewIn: {
            /**
             * Decisions
             * @default {}
             */
            decisions: {
                [key: string]: unknown;
            };
            /**
             * Kind
             * @enum {string}
             */
            kind: "daily" | "weekly";
            /** Note */
            note?: string | null;
            /**
             * Period Start
             * Format: date
             */
            period_start: string;
        };
        /** ReviewOut */
        app__modules__review__schemas__ReviewOut: {
            /** Decisions */
            decisions: {
                [key: string]: unknown;
            };
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "daily" | "weekly";
            /** Note */
            note: string | null;
            /**
             * Period End
             * Format: date
             */
            period_end: string;
            /**
             * Period Start
             * Format: date
             */
            period_start: string;
            /** Stats */
            stats: {
                [key: string]: unknown;
            };
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    activity_api_activity_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                since?: string | null;
                verbs?: string[] | null;
                category?: string | null;
                q?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activity_day_api_activity_day_get: {
        parameters: {
            query: {
                /** @description YYYY-MM-DD */
                day: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    activity_heatmap_api_activity_heatmap_get: {
        parameters: {
            query?: {
                days?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    applications_list_api_applications_get: {
        parameters: {
            query?: {
                status?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    applications_funnel_api_applications_funnel_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FunnelOut"];
                };
            };
        };
    };
    rejection_reasons_api_applications_rejection_reasons_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    application_transition_api_applications__item_id__transition_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TransitionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    github_credentials_api_auth_github_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GithubCredentialsIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    github_disconnect_api_auth_github_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    github_status_api_auth_github_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    disconnect_api_auth_google_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    callback_api_auth_google_callback_get: {
        parameters: {
            query: {
                code: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    auth_start_api_auth_google_start_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    status_api_auth_google_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    run_backup_api_backup_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    inspect_backup_api_backup_inspect_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_inspect_backup_api_backup_inspect_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_backup_api_backup_restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_restore_backup_api_backup_restore_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    backup_status_api_backup_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    list_bookmarks_api_bookmarks_get: {
        parameters: {
            query?: {
                collection?: string | null;
                read_status?: string | null;
                favorite?: boolean | null;
                source?: string | null;
                q?: string | null;
                tag?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bulk_action_bookmarks_api_bookmarks_bulk_action_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookmarkBulkActionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkBulkActionResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_bookmarks_api_bookmarks_export_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    import_bookmarks_api_bookmarks_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    [key: string]: unknown;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    bookmark_stats_api_bookmarks_stats_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkStats"];
                };
            };
        };
    };
    get_bookmark_api_bookmarks__bookmark_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_bookmark_api_bookmarks__bookmark_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_bookmark_api_bookmarks__bookmark_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookmarkUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    move_bookmark_api_bookmarks__bookmark_id__collection_patch: {
        parameters: {
            query: {
                collection: string;
            };
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    convert_bookmark_to_task_api_bookmarks__bookmark_id__convert_to_task_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConvertToTaskIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_note_from_bookmark_api_bookmarks__bookmark_id__create_note_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateNoteFromBookmarkIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    enrich_bookmark_api_bookmarks__bookmark_id__enrich_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_bookmark_fulltext_api_bookmarks__bookmark_id__fulltext_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkFullTextOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_bookmark_highlights_api_bookmarks__bookmark_id__highlights_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkHighlightOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_bookmark_highlight_api_bookmarks__bookmark_id__highlights_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookmarkHighlightIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkHighlightOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_bookmark_highlight_api_bookmarks__bookmark_id__highlights__highlight_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
                highlight_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    convert_highlight_to_flashcard_api_bookmarks__bookmark_id__highlights__highlight_id__convert_to_flashcard_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
                highlight_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_bookmark_progress_api_bookmarks__bookmark_id__progress_patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                bookmark_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookmarkProgressUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    calendar_events_api_calendar_events_get: {
        parameters: {
            query?: {
                from?: string;
                to?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_calendar_api_calendar_sync_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    capture_api_capture_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaptureIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaptureResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    career_connections_api_career_connections_get: {
        parameters: {
            query?: {
                search?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CareerConnectionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_career_connections_api_career_connections_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_career_connections_api_career_connections_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CareerConnectionsImportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cover_letter_review_api_career_cover_letter_review_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CoverLetterReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CoverLetterReviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    career_stories_api_career_stories_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CareerStoryOut"][];
                };
            };
        };
    };
    create_career_story_api_career_stories_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CareerStoryIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CareerStoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_career_story_api_career_stories__story_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                story_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_career_story_api_career_stories__story_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                story_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CareerStoryPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CareerStoryOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    courses_api_courses_get: {
        parameters: {
            query?: {
                include_archived?: boolean;
                area_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CourseOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_course_api_courses_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CourseIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CourseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_course_api_courses__course_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                course_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_course_api_courses__course_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                course_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CoursePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CourseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    deadlines_api_deadlines_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    documents_api_documents_get: {
        parameters: {
            query?: {
                category?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_api_documents_sync_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SyncIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_document_api_documents_upload_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_document_api_documents_upload_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    document_usages_api_documents_usages_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentUsagesOut"][];
                };
            };
        };
    };
    delete_document_api_documents__id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_document_file_api_documents__id__file_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    open_doc_api_documents__id__open_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    entity_detail_api_entities__entity_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EntityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    entity_backlinks_api_entities__entity_id__backlinks_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    related_api_entities__entity_id__related_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RelatedOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    expenses_api_expenses_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    add_expense_api_expenses_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExpenseIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_expense_api_expenses__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_expense_api_expenses__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExpensePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_bookmarks_api_export_bookmarks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    export_csv_api_export_csv_get: {
        parameters: {
            query: {
                module: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_ics_api_export_ics_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    export_json_api_export_json_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    export_markdown_api_export_markdown_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    export_opml_api_export_opml_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    overview_api_finance_overview_get: {
        parameters: {
            query?: {
                year?: number | null;
                month?: number | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    summary_api_finance_summary_get: {
        parameters: {
            query?: {
                months?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_card_api_flashcard_cards__card_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                card_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_card_api_flashcard_cards__card_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                card_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CardPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_api_flashcard_cards__card_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                card_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["app__modules__flashcard__schemas__ReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["app__modules__flashcard__schemas__ReviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cram_missed_api_flashcard_cram_missed_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CramCardOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decks_api_flashcard_decks_get: {
        parameters: {
            query?: {
                linked_to?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeckOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_deck_api_flashcard_decks_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeckIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeckOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_deck_api_flashcard_decks__deck_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                deck_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_deck_api_flashcard_decks__deck_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                deck_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeckPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeckOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cards_api_flashcard_decks__deck_id__cards_get: {
        parameters: {
            query?: {
                due?: boolean;
                /** @description Yalnizca en az bir kez unutulanlar */
                only_lapses?: boolean;
                q?: string | null;
            };
            header?: never;
            path: {
                deck_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CardOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_card_api_flashcard_decks__deck_id__cards_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                deck_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CardIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_cards_api_flashcard_import_post: {
        parameters: {
            query?: {
                deck?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_cards_api_flashcard_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    knowledge_graph_api_graph_get: {
        parameters: {
            query?: {
                focus?: string | null;
                depth?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    incomes_api_incomes_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    add_income_api_incomes_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IncomeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_income_api_incomes__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_income_api_incomes__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IncomePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_interview_api_interviews__interview_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                interview_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_interview_api_interviews__interview_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                interview_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InterviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InterviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_resource_api_learning_resources__resource_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                resource_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_resource_api_learning_resources__resource_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                resource_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_resource_api_learning_resources__resource_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                resource_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResourcePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_link_api_links_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LinkIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_link_api_links_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LinkIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_media_api_media_get: {
        parameters: {
            query?: {
                kind?: string | null;
                status?: string | null;
                q?: string | null;
                collection_id?: string | null;
                tag?: string | null;
                owned?: boolean | null;
                favorite?: boolean | null;
                monitored?: boolean | null;
                provider?: string | null;
                trashed?: boolean;
                sort?: "updated" | "created" | "title" | "score" | "progress" | "relevance";
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaPageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_media_api_media_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaItemIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_artwork_proxy_api_media_artwork_proxy_get: {
        parameters: {
            query: {
                url: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_artwork_prune_api_media_artwork_prune_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaArtworkPruneOut"];
                };
            };
        };
    };
    media_artwork_stats_api_media_artwork_stats_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaArtworkStatsOut"];
                };
            };
        };
    };
    media_asset_api_media_assets__asset_name__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_name: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    collections_api_media_collections_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaCollectionOut"][];
                };
            };
        };
    };
    create_collection_api_media_collections_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaCollectionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaCollectionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    collection_detail_api_media_collections__collection_id__get: {
        parameters: {
            query?: {
                q?: string | null;
                sort?: "updated" | "created" | "title" | "score" | "progress";
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path: {
                collection_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaCollectionDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_collection_api_media_collections__collection_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                collection_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_collection_api_media_collections__collection_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                collection_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaCollectionUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaCollectionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_collection_item_api_media_collections__collection_id__items__item_id__post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                collection_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_collection_item_api_media_collections__collection_id__items__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                collection_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_dashboard_api_media_dashboard_get: {
        parameters: {
            query?: {
                range?: "week" | "month" | "90d" | "year" | "all";
                recent_limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaDashboardOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_providers_api_media_providers_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaProviderStatusOut"][];
                };
            };
        };
    };
    search_all_metadata_api_media_search_global_get: {
        parameters: {
            query: {
                q: string;
                kind?: string | null;
                provider?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GlobalMetadataSearchOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_stats_api_media_stats_get: {
        parameters: {
            query?: {
                range?: "week" | "month" | "90d" | "year" | "all";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaStats"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    queue_media_sync_api_media_sync_post: {
        parameters: {
            query?: {
                provider?: string | null;
                item_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaSyncBatchOut"] | components["schemas"]["MediaSyncIdleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_upcoming_api_media_upcoming_get: {
        parameters: {
            query?: {
                days?: number | null;
                kind?: string | null;
                provider?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaUpcomingPageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_detail_api_media__item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    trash_media_api_media__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_media_api_media__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaItemUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_consumptions_api_media__item_id__consumptions_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaConsumptionPageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    consume_media_api_media__item_id__consumptions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaConsumptionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaConsumptionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_cycles_api_media__item_id__cycles_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaCycleOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_media_cycle_api_media__item_id__cycles_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaCycleStart"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaCycleOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    permanent_delete_media_api_media__item_id__permanent_delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_media_api_media__item_id__restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_milestone_api_milestones__milestone_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                milestone_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_milestone_api_milestones__milestone_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                milestone_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MilestonePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    github_trending_api_news_github_trending_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    hacker_news_api_news_hacker_news_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reddit_news_api_news_reddit_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_note_folders_api_note_folders_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteFolderOut"][];
                };
            };
        };
    };
    create_note_folder_api_note_folders_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteFolderIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteFolderOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_note_folder_api_note_folders__folder_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                folder_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_note_folder_api_note_folders__folder_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                folder_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteFolderUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteFolderOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_notes_api_notes_get: {
        parameters: {
            query?: {
                include_archived?: boolean;
                about?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_note_api_notes_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_note_api_notes__note_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_note_api_notes__note_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_note_api_notes__note_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_note_api_notes__note_id__archive_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"] | null;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_attachment_api_notes__note_id__attachments_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_attachment_api_notes__note_id__attachments_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteAttachmentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_attachment_api_notes__note_id__attachments__attachment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_attachment_api_notes__note_id__attachments__attachment_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                note_id: string;
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    notifications_api_notifications_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NotificationOut"][];
                };
            };
        };
    };
    dismiss_all_notifications_api_notifications_dismiss_all_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    read_all_notifications_api_notifications_read_all_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    dismiss_notification_api_notifications__notification_id__dismiss_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notification_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_notification_api_notifications__notification_id__read_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notification_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunities_api_opportunities_get: {
        parameters: {
            query?: {
                status?: string | null;
                kind?: string | null;
                limit?: number;
                trashed_only?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_api_opportunities_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpportunityIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunity_browse_api_opportunities_browse_get: {
        parameters: {
            query?: {
                section?: string;
                announcement_source?: string | null;
                category?: string | null;
                search?: string | null;
                status?: string | null;
                source?: string | null;
                region?: string | null;
                remote?: string | null;
                archetype?: string | null;
                recommendation?: string | null;
                period_days?: number | null;
                year?: number | null;
                min_score?: number | null;
                max_score?: number | null;
                skill?: string | null;
                min_skill_match?: number | null;
                max_skill_match?: number | null;
                skill_match_state?: ("any" | "computed" | "uncomputed") | null;
                source_status?: "active" | "stale" | "all";
                sort?: string;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityBrowseOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    followups_api_opportunities_followups_get: {
        parameters: {
            query?: {
                days?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FollowupOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunity_lifecycle_api_opportunities_lifecycle_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    prune_opportunities_api_opportunities_prune_post: {
        parameters: {
            query: {
                days?: number;
                confirm_token: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PruneResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    prune_preview_api_opportunities_prune_preview_get: {
        parameters: {
            query?: {
                days?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PrunePreviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    silent_applications_api_opportunities_silence_get: {
        parameters: {
            query?: {
                days?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SilentApplicationOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunity_detail_api_opportunities__item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_api_opportunities__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_api_opportunities__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpportunityPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    application_detail_api_opportunities__item_id__application_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    application_update_api_opportunities__item_id__application_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApplicationIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    apply_api_opportunities__item_id__apply_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApplyIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    connections_for_opportunity_api_opportunities__item_id__connections_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityConnectionsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_evaluation_api_opportunities__item_id__evaluation_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpportunityEvaluationPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityEvaluationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_evaluation_api_opportunities__item_id__evaluation_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityEvaluationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    history_api_opportunities__item_id__history_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HistoryOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    interviews_api_opportunities__item_id__interviews_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InterviewOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_interview_api_opportunities__item_id__interviews_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InterviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InterviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunity_notes_api_opportunities__item_id__notes_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reply_analysis_api_opportunities__item_id__reply_analysis_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReplyAnalysisIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReplyAnalysisOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    requirements_api_opportunities__item_id__requirements_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequirementOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    requirement_api_opportunities__item_id__requirements_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequirementIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequirementOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_or_create_research_note_api_opportunities__item_id__research_note_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NoteOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_api_opportunities__item_id__restore_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunity_salary_consistency_api_opportunities__item_id__salary_consistency_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SalaryConsistencyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    application_timeline_api_opportunities__item_id__timeline_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationTimelineOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    opportunity_todos_api_opportunities__item_id__todos_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodoOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_opportunity_todo_api_opportunities__item_id__todos_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TodoIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodoOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    transition_api_opportunities__item_id__transition_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TransitionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    trash_api_opportunities__item_id__trash_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_plan_api_plan_get: {
        parameters: {
            query?: {
                week?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanSlotOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_slot_api_plan_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanSlotIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanSlotOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    carry_over_api_plan_carry_over_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CarryOverIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_slot_api_plan__slot_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slot_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_slot_api_plan__slot_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slot_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanSlotUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanSlotOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    push_plan_api_plan__slot_id__push_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slot_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_manual_api_pomodoro_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PomodoroManual"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    active_api_pomodoro_active_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"] | null;
                };
            };
        };
    };
    contexts_api_pomodoro_contexts_get: {
        parameters: {
            query?: {
                q?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContextOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sessions_api_pomodoro_sessions_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_api_pomodoro_start_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PomodoroStart"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stats_api_pomodoro_stats_get: {
        parameters: {
            query?: {
                range?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroStats"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_api_pomodoro__pomo_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                pomo_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pause_api_pomodoro__pomo_id__pause_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                pomo_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    resume_api_pomodoro__pomo_id__resume_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                pomo_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stop_api_pomodoro__pomo_id__stop_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                pomo_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PomodoroStop"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PomodoroOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    projects_api_projects_get: {
        parameters: {
            query?: {
                status?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_project_api_projects_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_project_api_projects__project_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_project_api_projects__project_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    project_github_api_projects__project_id__github_get: {
        parameters: {
            query?: {
                refresh?: boolean;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    issue_to_todo_api_projects__project_id__github_issues_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IssueToTodoIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    project_journal_api_projects__project_id__journal_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    put_project_journal_note_api_projects__project_id__journal__day__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                day: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectJournalNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_milestone_api_projects__project_id__milestones_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MilestoneIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    project_todos_api_projects__project_id__todos_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_project_todo_api_projects__project_id__todos_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TodoLinkIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    recurring_api_recurring_payments_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    add_recurring_api_recurring_payments_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecurringIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_recurring_api_recurring_payments__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_recurring_api_recurring_payments__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecurringPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pay_api_recurring_payments__item_id__pay_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    registry_entity_types_api_registry_entity_types_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    registry_event_verbs_api_registry_event_verbs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    bind_requirement_document_api_requirements__requirement_id__document_patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                requirement_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequirementDocumentIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequirementOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_reviews_api_reviews_get: {
        parameters: {
            query?: {
                kind?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["app__modules__review__schemas__ReviewOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_review_api_reviews_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["app__modules__review__schemas__ReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["app__modules__review__schemas__ReviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_api_reviews_preview_get: {
        parameters: {
            query?: {
                kind?: string;
                period_start?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewPreview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_feeds_api_rss_feeds_get: {
        parameters: {
            query?: {
                category?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_feed_api_rss_feeds_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeedIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_feed_api_rss_feeds__feed_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feed_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_feed_api_rss_feeds__feed_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feed_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeedUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_feed_api_rss_feeds__feed_id__refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feed_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_opml_api_rss_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_opml_api_rss_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_items_api_rss_items_get: {
        parameters: {
            query?: {
                feed_id?: string | null;
                category?: string | null;
                unread_only?: boolean;
                saved_only?: boolean;
                since?: string | null;
                q?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedItemOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_item_api_rss_items__item_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    item_full_text_api_rss_items__item_id__fulltext_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_read_api_rss_items__item_id__read_post: {
        parameters: {
            query?: {
                read?: boolean;
            };
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FeedItemOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    save_item_api_rss_items__item_id__save_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SaveItemIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BookmarkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_all_read_api_rss_read_all_post: {
        parameters: {
            query?: {
                feed_id?: string | null;
                category?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_all_api_rss_refresh_all_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    rss_stats_api_rss_stats_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RssStats"];
                };
            };
        };
    };
    search_api_search_get: {
        parameters: {
            query: {
                q: string;
                types?: string[] | null;
                limit?: number;
                grouped?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    settings_api_settings_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    reset_settings_api_settings_reset_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    put_setting_api_settings__key__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SettingIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    source_cache_stats_api_sources_cache_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    source_cache_clear_api_sources_cache_clear_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CacheClearIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    source_cache_prune_api_sources_cache_prune_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CachePruneIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    source_catalog_api_sources_catalog_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    source_coverage_api_sources_coverage_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    source_health_api_sources_health_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceRunOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    jobhunter_config_api_sources_jobhunter_config_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    jobhunter_config_update_api_sources_jobhunter_config_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": {
                    [key: string]: unknown;
                };
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    jobhunter_env_api_sources_jobhunter_env_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    jobhunter_linkedin_profiles_api_sources_jobhunter_linkedin_profiles_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    jobhunter_linkedin_profiles_save_api_sources_jobhunter_linkedin_profiles_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": unknown[];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_sources_api_sources_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SourceRefreshIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceRefreshResult"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    source_runs_api_sources_runs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    sync_status_api_sources_sync_get: {
        parameters: {
            query?: {
                scope?: "opportunity" | "media";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceSyncStatusOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_history_api_sources_sync_history_get: {
        parameters: {
            query?: {
                limit?: number;
                scope?: "opportunity" | "media";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceSyncBatchOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_source_api_sources__source_id__refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    statistics_monthly_api_statistics_monthly_get: {
        parameters: {
            query?: {
                months?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MonthlyPoint"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    statistics_summary_api_statistics_summary_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StatisticsSummary"];
                };
            };
        };
    };
    areas_api_study_areas_get: {
        parameters: {
            query?: {
                include_stats?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyAreaOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_area_api_study_areas_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AreaIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyAreaOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_area_api_study_areas__area_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                area_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_area_api_study_areas__area_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                area_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AreaPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyAreaOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    area_tree_api_study_areas__area_id__tree_get: {
        parameters: {
            query?: {
                q?: string | null;
                status?: string | null;
                include_resources?: boolean;
            };
            header?: never;
            path: {
                area_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyTreeOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_topics_api_study_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TopicImportIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TopicImportOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_preview_api_study_import_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TopicImportIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportPreviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    attach_bookmark_api_study_resources_attach_bookmark_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AttachBookmarkIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_queue_api_study_review_get: {
        parameters: {
            query?: {
                window?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewQueueOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stale_api_study_stale_get: {
        parameters: {
            query?: {
                days?: number;
                limit?: number;
                offset?: number;
                area_id?: string | null;
                include_done?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StalePageOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    study_stats_api_study_stats_get: {
        parameters: {
            query?: {
                range?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyStatsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    topics_api_study_topics_get: {
        parameters: {
            query: {
                area_id: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyTopicLegacyNode"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_topic_api_study_topics_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TopicIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyTopicOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    topic_api_study_topics__topic_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyTopicDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_topic_api_study_topics__topic_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_topic_api_study_topics__topic_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TopicPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyTopicOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    topic_impact_api_study_topics__topic_id__impact_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TopicImpactOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    move_topic_api_study_topics__topic_id__move_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TopicMoveIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudyTopicOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    topic_progress_api_study_topics__topic_id__progress_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TopicProgressOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    topic_resources_api_study_topics__topic_id__resources_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResourceOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_resource_api_study_topics__topic_id__resources_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResourceIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_topic_api_study_topics__topic_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TopicReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TopicReviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_topic_todo_api_study_topics__topic_id__todos_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["TopicTodoIn"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TopicTodoOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    manual_refresh_status_api_system_refresh_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManualRefreshOut"];
                };
            };
        };
    };
    manual_refresh_api_system_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ManualRefreshIn"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ManualRefreshOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    system_stats_api_system_stats_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    list_tags_api_tags_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagOut"][];
                };
            };
        };
    };
    agenda_api_today_agenda_get: {
        parameters: {
            query?: {
                day?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodayAgendaOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_todos_api_todos_get: {
        parameters: {
            query?: {
                status?: string | null;
                due_before?: string | null;
                priority?: number | null;
                include_undated?: boolean;
                completed_after?: string | null;
                recur_only?: boolean;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodoOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_todo_api_todos_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TodoIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodoOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_todo_api_todos__todo_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                todo_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_todo_api_todos__todo_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                todo_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TodoUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodoOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_todo_api_todos__todo_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                todo_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TodoOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_views_api_views_get: {
        parameters: {
            query?: {
                module?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedViewOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_view_api_views_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedViewCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedViewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_view_api_views__view_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                view_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_view_api_views__view_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                view_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SavedViewPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SavedViewOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    weather_forecast_api_weather_forecast_get: {
        parameters: {
            query: {
                lat: number;
                lon: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    weather_geocode_api_weather_geocode_get: {
        parameters: {
            query?: {
                query?: string | null;
                lat?: number | null;
                lon?: number | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GeocodeOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
}
