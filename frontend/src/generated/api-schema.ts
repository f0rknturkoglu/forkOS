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
         *     `filter` urun alanidir (tasks/focus/learning/reading/career/system);
         *     ayrica "alerts" dikkat gerektiren kayitlari verir -- bu suzme SUNUCUDA
         *     yapilir, istemci yalnizca ilk sayfayi suzmez. "all" ya da bos birakmak
         *     filtre uygulamaz. `q` baslik/verb/payload icinde arar; `offset` ile
         *     "daha fazla yukle" yapilir. Ayni kayit iki kez gelmesin diye sira
         *     (occurred_at, id) sabittir.
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
    "/api/agent/continuity/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Continuity Status */
        get: operations["continuity_status_api_agent_continuity_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/episode/finalize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Episode Finalize
         * @description Oturumu mühürler. İdempotenttir: ikinci çağrı aynı mühürlü kaydı döndürür.
         */
        post: operations["episode_finalize_api_agent_episode_finalize_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/episode/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Episode Status
         * @description Metadata-only tanılama: son mühürleme, ifade sayısı, taslak sayısı.
         */
        get: operations["episode_status_api_agent_episode_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/episode/turn": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Episode Turn
         * @description `post_llm_call` gözlemi: turu damıtır ve yalnız türetilmiş ifadeleri yazar.
         *
         *     Ham `user_message`/`assistant_response` yanıtta DÖNMEZ; yalnız sayaç ve
         *     sınırlı gerekçe kodları döner.
         */
        post: operations["episode_turn_api_agent_episode_turn_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/lifecycle/event": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Lifecycle Event */
        post: operations["lifecycle_event_api_agent_lifecycle_event_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/lifecycle/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Lifecycle Status */
        get: operations["lifecycle_status_api_agent_lifecycle_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/lifecycle/turn": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Lifecycle Turn */
        post: operations["lifecycle_turn_api_agent_lifecycle_turn_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Candidates
         * @description Kayıtlı semantik hafıza adaylarını listeler.
         */
        get: operations["list_candidates_api_agent_semantic_candidates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/candidates/{candidate_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Candidate
         * @description Belirli bir adayın detayını döner.
         */
        get: operations["get_candidate_api_agent_semantic_candidates__candidate_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/candidates/{candidate_id}/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Confirm Candidate
         * @description Adayı kullanıcı tarafından onaylanmış ('ready') olarak işaretler.
         */
        post: operations["confirm_candidate_api_agent_semantic_candidates__candidate_id__confirm_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/candidates/{candidate_id}/promote": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Promote Candidate
         * @description Adayı kalıcı bilgiye terfi ettirir.
         */
        post: operations["promote_candidate_api_agent_semantic_candidates__candidate_id__promote_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/candidates/{candidate_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reject Candidate
         * @description Adayı reddeder ('rejected').
         */
        post: operations["reject_candidate_api_agent_semantic_candidates__candidate_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh Candidates
         * @description Mühürlenmiş epizotlardan ve kanonik kaynaklardan adayları tazeler.
         */
        post: operations["refresh_candidates_api_agent_semantic_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/semantic/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Status
         * @description Semantik hafıza durumu ve özet istatistikleri döner.
         */
        get: operations["get_status_api_agent_semantic_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agent/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Agent Status
         * @description Ajan yetenek haritasi + yerel bilis durumu (salt okunur teshis).
         *
         *     Adres gercek baglanma portundan kurulur (`scope["server"]`), Host
         *     basligindan DEGIL: arayuz hangi adresten baglanacagini boylece dogru
         *     ogrenir. H4 kapaliyken hicbir ag cagrisi yapilmaz.
         */
        get: operations["agent_status_api_agent_status_get"];
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
         *     Keşfedilmiş ilanlar buraya hiçbir koşulda girmez (Faz 4.1). Yanıt bir
         *     zarftır: `items` sayfayı, `total` filtrenin GERÇEK toplamını taşır; aksi
         *     halde 120'lik limit "tüm başvurular" gibi okunurdu.
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
    "/api/bookmarks/{bookmark_id}/source-note": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Source Note
         * @description Yer iminin kanonik Vault kaynak notunu çözer veya oluşturur.
         *
         *     Yer imi ve vurguları forkOS'ta operasyonel kalır; burada yalnızca bir Vault
         *     dosyası üretilir. forkOS veritabanında not kaydı OLUŞMAZ.
         */
        post: operations["create_source_note_api_bookmarks__bookmark_id__source_note_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/api/career/cover-letters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Career Cover Letters
         * @description Kaydedilmiş ön yazılar: TEK istek (panel başına kayıt-başına istek yok).
         */
        get: operations["career_cover_letters_api_career_cover_letters_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/interview-prep": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Career Interview Prep
         * @description Mülakat hazırlığı grupları: görüşmeler + maaş tutarlılığı TEK turda.
         */
        get: operations["career_interview_prep_api_career_interview_prep_get"];
        put?: never;
        post?: never;
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
         *
         *     Bilgi grafi GORSELLESTIRMESI PHASE 3'te kaldirildi (`/graph` ucu yok);
         *     bu okuma operasyonel yuzeyler (`BacklinksPanel`) icin kalir.
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
    "/api/execution/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plans */
        get: operations["list_plans_api_execution_plans_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Plan */
        get: operations["get_plan_api_execution_plans__plan_row_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve */
        post: operations["approve_api_execution_plans__plan_row_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel */
        post: operations["cancel_api_execution_plans__plan_row_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}/execute": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Execute */
        post: operations["execute_api_execution_plans__plan_row_id__execute_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}/recover": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Recover
         * @description Çökmüş yürütmeyi kurtarır; canlı yürütücü DEVRALINMAZ.
         */
        post: operations["recover_api_execution_plans__plan_row_id__recover_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject */
        post: operations["reject_api_execution_plans__plan_row_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/execution/plans/{plan_row_id}/respond": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Respond */
        post: operations["respond_api_execution_plans__plan_row_id__respond_post"];
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
    "/api/obsidian/capture": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Capture Note
         * @description Hızlı yakalanan bilgi notunu doğrudan Vault'ta (`00 Inbox/`) oluşturur.
         *
         *     Kimliği sunucu üretir; forkOS veritabanında not kaydı OLUŞMAZ. İlişki
         *     hedefi (`relate_to`) sunucuda çözülür, istemcinin verdiği tip/başlık
         *     kullanılmaz.
         */
        post: operations["capture_note_api_obsidian_capture_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/obsidian/ensure": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Ensure Item
         * @description Kanonik bilgi notunu (varsa) çözer, yoksa oluşturur.
         *
         *     Başlık ve tip istemciden alınmaz; `entity` tablosundan çözülür. Aynı
         *     kimlikle ikinci çağrı yeni dosya üretmez.
         */
        post: operations["ensure_item_api_obsidian_ensure_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/obsidian/index/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh Index
         * @description Obsidian Vault dizinini yeniden tarar ve bellek içi indeksi tazeler.
         */
        post: operations["refresh_index_api_obsidian_index_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/obsidian/items/{forkos_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Item
         * @description Belirtilen forkOS ID'sine karşılık gelen Vault dosyasını ve açılış URI'sini döner.
         */
        get: operations["get_item_api_obsidian_items__forkos_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/obsidian/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Status
         * @description Obsidian Vault entegrasyonunun durumu ve Obsidian bağlantıları.
         *
         *     Path'in tam sistem yolunu browser'a ifşa etmez.
         */
        get: operations["get_status_api_obsidian_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/obsidian/uri/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Uri For
         * @description Vault içi arama URI'si. Parametre kodlaması sunucuda yapılır.
         */
        get: operations["search_uri_for_api_obsidian_uri_search_get"];
        put?: never;
        post?: never;
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
    "/api/opportunities/{id}/application-package": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Opportunity Application Package
         * @description Fırsatın hazırlanmış başvuru paketini ve hazırlık durumunu getir (C5).
         */
        get: operations["get_opportunity_application_package_api_opportunities__id__application_package_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{id}/application-package/resolve-answer": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resolve Application Package Answer
         * @description Kullanıcı girdisi bekleyen başvuru sorusunu yanıtla ve hazır olma durumunu güncelle (C5).
         */
        post: operations["resolve_application_package_answer_api_opportunities__id__application_package_resolve_answer_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{id}/deep-evaluate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Evaluate Opportunity Deep
         * @description Fırsatın aday profili ve kanıtlarıyla derin uyumunu değerlendir (C4).
         */
        post: operations["evaluate_opportunity_deep_api_opportunities__id__deep_evaluate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{id}/deep-evaluation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Opportunity Deep Evaluation
         * @description Fırsatın güncel derin değerlendirmesini ve bayatlık durumunu getir (C4).
         */
        get: operations["get_opportunity_deep_evaluation_api_opportunities__id__deep_evaluation_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{id}/extract-jd": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Extract Opportunity Jd
         * @description Fırsatın iş ilanı metnini çıkar ve açıklama taslaksa kanonik açıklamaya yükselt.
         */
        post: operations["extract_opportunity_jd_api_opportunities__id__extract_jd_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{id}/liveness": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Check Opportunity Liveness
         * @description Fırsatın kaynak linklerinin canlılığını doğrula ve durumunu güncelle.
         */
        post: operations["check_opportunity_liveness_api_opportunities__id__liveness_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/opportunities/{id}/prepare-package": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Prepare Opportunity Application Package
         * @description Fırsat için başvuru paketini (uyarlanmış CV, ön yazı, soru yanıtları) hazırla (C5).
         */
        post: operations["prepare_opportunity_application_package_api_opportunities__id__prepare_package_post"];
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
        /**
         * Get Or Create Research Note
         * @description Fırsatın kanonik araştırma notunu çözer, yoksa Vault'ta oluşturur.
         *
         *     Kimlik fırsatın UUID'sidir: aynı fırsat için ikinci dosya üretilmez.
         *     forkOS veritabanında not kaydı OLUŞMAZ; not `00 Inbox/` altında yaşar ve
         *     frontmatter'ında `notes_about` ilişkisini taşır (PHASE 3 §38).
         */
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
    "/api/pomodoro/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Analytics */
        get: operations["analytics_api_pomodoro_analytics_get"];
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
    "/api/proactivity/config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Config */
        put: operations["put_config_api_proactivity_config_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/proactivity/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get History */
        get: operations["get_history_api_proactivity_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/proactivity/rules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Rules */
        get: operations["get_rules_api_proactivity_rules_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/proactivity/rules/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Rule */
        put: operations["put_rule_api_proactivity_rules__kind__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/proactivity/rules/{kind}/snooze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Snooze Rule
         * @description Kural duzeyinde override: "bu hafta dürtme" (§26/§108).
         */
        post: operations["snooze_rule_api_proactivity_rules__kind__snooze_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/proactivity/runs/{run_id}/snooze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Snooze Run */
        post: operations["snooze_run_api_proactivity_runs__run_id__snooze_post"];
        /** Unsnooze Run */
        delete: operations["unsnooze_run_api_proactivity_runs__run_id__snooze_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/proactivity/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Status */
        get: operations["get_status_api_proactivity_status_get"];
        put?: never;
        post?: never;
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
    "/api/projects/{project_id}/journal/{day}/obsidian": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Open Project Journal In Obsidian
         * @description Proje günlüğünün Vault dosyasını çözer, yoksa oluşturur.
         *
         *     Günlük METNİ forkOS'ta tutulmaz: sahibi Vault'tur ve düzenleme Obsidian'da
         *     yapılır. PHASE 2 ile taşınmış günlükler `forkos_id`'leriyle yeniden
         *     kullanılır; aynı gün için ikinci dosya üretilmez.
         */
        post: operations["open_project_journal_in_obsidian_api_projects__project_id__journal__day__obsidian_post"];
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
    "/api/recurring-payments/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Recurring History */
        get: operations["recurring_history_api_recurring_payments_history_get"];
        put?: never;
        post?: never;
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
    "/api/reviews/{review_id}": {
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
        /** Patch Review Note */
        patch: operations["patch_review_note_api_reviews__review_id__patch"];
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
    "/api/system/automation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Automation State
         * @description Arka plan otomasyonu durumu (arayuz icin tek okuma).
         *
         *     `modules.disabled`'tan AYRI: gorunurluk ve ag trafigi farkli sorulardir.
         */
        get: operations["automation_state_api_system_automation_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/automation/profile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Set Automation Profile
         * @description Profili uygula (manual/balanced/active): ilgili ayarlar birlikte yazilir.
         */
        post: operations["set_automation_profile_api_system_automation_profile_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/career-ops/doctor": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Career Ops Doctor
         * @description career-ops yetenek motoru tanı ve durum raporu (salt okunur).
         */
        get: operations["career_ops_doctor_api_system_career_ops_doctor_get"];
        put?: never;
        post?: never;
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
    "/api/system/storage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * System Storage
         * @description Depolama dokumu + esik uyarilari (diagnostics; polling icin DEGIL).
         */
        get: operations["system_storage_api_system_storage_get"];
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
        /**
         * ActivityEventOut
         * @description Akis kaydi + sunucu tarafi uyari bayragi.
         *
         *     Uyari kurali istemcide TEKRARLANMAZ: hangi fiilin uyari oldugu tek
         *     kaynaktan (core/events.ALERT_VERBS + payload kurali) burada isaretlenir.
         */
        ActivityEventOut: {
            /** Entity Id */
            entity_id: string | null;
            /** Entity Type */
            entity_type: string | null;
            /** Id */
            id: number;
            /**
             * Is Alert
             * @default false
             */
            is_alert: boolean;
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
            /** Entity Id */
            entity_id?: string | null;
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
            kind: "calendar" | "todo" | "rss" | "media" | "opportunity" | "interview" | "payment" | "study" | "flashcard" | "pomodoro";
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
            /** Career */
            career?: components["schemas"]["AgendaRow"][];
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
        /**
         * AgentStatusOut
         * @description `GET /api/agent/status` govdesi.
         */
        AgentStatusOut: {
            brain: components["schemas"]["BrainStatusOut"];
            local_cognition: components["schemas"]["LocalCognitionOut"];
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
        /** ApplicationAnswerOut */
        ApplicationAnswerOut: {
            /**
             * Classification
             * @enum {string}
             */
            classification: "safe_verified" | "needs_user_input" | "sensitive_user_decision";
            /**
             * Confidence
             * @default 1
             */
            confidence: number;
            /** Evidence Refs */
            evidence_refs?: string[];
            /** Proposed Answer */
            proposed_answer: string;
            /** Question */
            question: string;
            /** Warning */
            warning?: string | null;
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
        /**
         * ApplicationListOut
         * @description Basvuru listesi ZARFI. Limitli liste "toplam" gibi sunulmaz.
         */
        ApplicationListOut: {
            /** Items */
            items: components["schemas"]["OpportunityOut"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
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
        /** ApplicationPackageOut */
        ApplicationPackageOut: {
            /** Application Answers */
            application_answers?: components["schemas"]["ApplicationAnswerOut"][];
            /** Base Cv Document Id */
            base_cv_document_id?: string | null;
            /**
             * Cover Letter
             * @default
             */
            cover_letter: string;
            /** Created At */
            created_at: string;
            /** Cv Change Audit */
            cv_change_audit?: components["schemas"]["CvChangeItemOut"][];
            /** Evaluation Revision */
            evaluation_revision: string;
            /** Fact Verification */
            fact_verification?: components["schemas"]["CvFactVerificationOut"][];
            /** Generated Documents */
            generated_documents?: components["schemas"]["GeneratedDocumentRefOut"][];
            /** Knockout Answers */
            knockout_answers?: components["schemas"]["KnockoutAnswerOut"][];
            /** Listing Fingerprint */
            listing_fingerprint: string;
            /** Opportunity Id */
            opportunity_id: string;
            /** Provenance */
            provenance?: {
                [key: string]: unknown;
            };
            /**
             * Readiness
             * @enum {string}
             */
            readiness: "READY" | "NEEDS_INPUT" | "UNSUPPORTED_CLAIMS" | "STALE_EVALUATION" | "RENDER_FAILED";
            /** Tailored Cv */
            tailored_cv?: {
                [key: string]: unknown;
            };
            /** Updated At */
            updated_at: string;
            /** Warnings */
            warnings?: string[];
        };
        /**
         * ApplicationReviewStats
         * @description Kariyer metrikleri. ORAN YOK: kucuk orneklemde yuzde yanilticidir.
         */
        ApplicationReviewStats: {
            /**
             * Applied
             * @default 0
             */
            applied: number;
            /**
             * Career Prep
             * @default 0
             */
            career_prep: number;
            /** Discovered */
            discovered: number;
            /**
             * Interview
             * @default 0
             */
            interview: number;
            /**
             * Offer
             * @default 0
             */
            offer: number;
            /**
             * Prepared
             * @default 0
             */
            prepared: number;
            /**
             * Rejected
             * @default 0
             */
            rejected: number;
            /**
             * Shortlisted
             * @default 0
             */
            shortlisted: number;
            /**
             * Upcoming Deadlines
             * @default 0
             */
            upcoming_deadlines: number;
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
        /** AutomationProfileIn */
        AutomationProfileIn: {
            /** Profile */
            profile: string;
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
            /**
             * Position End
             * @default 0
             */
            position_end: number;
            /**
             * Position Start
             * @default 0
             */
            position_start: number;
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
            /**
             * Position End
             * @default 0
             */
            position_end: number;
            /**
             * Position Start
             * @default 0
             */
            position_start: number;
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
        /** BootstrapContinuity */
        BootstrapContinuity: {
            /** Active Threads */
            active_threads?: string[];
            /** Activity Gap Hours */
            activity_gap_hours?: number | null;
            /** Anchor Kind */
            anchor_kind?: string | null;
            /** Anchor Timestamp */
            anchor_timestamp?: string | null;
            /** Last Meaningful Activity */
            last_meaningful_activity?: string | null;
            /** Recent Completed */
            recent_completed?: string[];
            /** Stalled Projects */
            stalled_projects?: string[];
        };
        /** BootstrapDiagnostics */
        BootstrapDiagnostics: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Degraded Reasons */
            degraded_reasons?: string[];
            /**
             * Generation Ms
             * @default 0
             */
            generation_ms: number;
            /**
             * Omitted Count
             * @default 0
             */
            omitted_count: number;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
        };
        /** BootstrapHotMemory */
        BootstrapHotMemory: {
            /** Items */
            items?: {
                [key: string]: unknown;
            }[];
        };
        /** BootstrapIdentity */
        BootstrapIdentity: {
            /** Durable Preferences */
            durable_preferences?: string[];
            /** Explicit Corrections */
            explicit_corrections?: string[];
            /** Interaction Conventions */
            interaction_conventions?: string[];
            /** Long Running Goals */
            long_running_goals?: string[];
        };
        /** BootstrapPacketV1 */
        BootstrapPacketV1: {
            continuity: components["schemas"]["BootstrapContinuity"];
            diagnostics: components["schemas"]["BootstrapDiagnostics"];
            /** Generated At */
            generated_at: string;
            hot_memory: components["schemas"]["BootstrapHotMemory"];
            identity: components["schemas"]["BootstrapIdentity"];
            /**
             * Is First Turn
             * @default true
             */
            is_first_turn: boolean;
            operational_state: components["schemas"]["OperationalState"];
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: 1;
            /** Session Key */
            session_key: string;
            /** Sources */
            sources?: components["schemas"]["BootstrapSourceRef"][];
        };
        /** BootstrapSourceRef */
        BootstrapSourceRef: {
            /** Scope Project */
            scope_project?: string | null;
            /** Source Id */
            source_id: string;
            /** Source Type */
            source_type: string;
            /** Source Version */
            source_version?: string | null;
            /** Title */
            title?: string | null;
        };
        /**
         * BrainStatusOut
         * @description MCP Brain Interface kimligi ve yetenek haritasi.
         */
        BrainStatusOut: {
            /** Endpoint */
            endpoint: string;
            /** Families */
            families: components["schemas"]["FamilyOut"][];
            /** Loopback Only */
            loopback_only: boolean;
            /** Server Name */
            server_name: string;
            /** Tool Count */
            tool_count: number;
            /** Transport */
            transport: string;
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
        /**
         * CaptureNoteIn
         * @description Hızlı yakalama: yeni bilgi notu (kimliği sunucu üretir).
         */
        CaptureNoteIn: {
            /** Body */
            body: string;
            /** Relate To */
            relate_to?: string | null;
            /** Tags */
            tags?: string[];
            /** Title */
            title?: string | null;
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
        /** ContinuityStatusOut */
        ContinuityStatusOut: {
            /** Active Source Count */
            active_source_count: number;
            /** Available */
            available: boolean;
            /** Degraded Reasons */
            degraded_reasons: string[];
            /** Has Active Continuity */
            has_active_continuity: boolean;
            /** Is Truncated */
            is_truncated: boolean;
            /** Last Bootstrap At */
            last_bootstrap_at: string | null;
            /** Last Context At */
            last_context_at?: string | null;
            /** Last Harness */
            last_harness: string | null;
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
        /**
         * CoverLetterOut
         * @description Kaydedilmis on yazi. Panel bunlari TEK istekle alir.
         */
        CoverLetterOut: {
            /** Cover Letter */
            cover_letter: string;
            /**
             * Opportunity Id
             * Format: uuid
             */
            opportunity_id: string;
            /** Organization */
            organization?: string | null;
            /** Title */
            title: string;
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
        /**
         * CreateSourceNoteIn
         * @description Kanonik kaynak notu isteği.
         *
         *     `pinned` KALDIRILDI (PHASE 3 §14): forkOS'ta sabitlenecek bir Notlar
         *     listesi kalmadı. Ek metin isteğe bağlı olarak not başlangıcına eklenir.
         */
        CreateSourceNoteIn: {
            /** Additional Text */
            additional_text?: string | null;
        };
        /** CvChangeItemOut */
        CvChangeItemOut: {
            /**
             * Change Type
             * @enum {string}
             */
            change_type: "added" | "removed" | "rewritten" | "reordered";
            /** Evidence Refs */
            evidence_refs?: string[];
            /** New */
            new: string;
            /** Original */
            original: string;
            /** Reason */
            reason: string;
        };
        /** CvFactVerificationOut */
        CvFactVerificationOut: {
            /** Candidate Fact Ref */
            candidate_fact_ref?: string | null;
            /** Claim */
            claim: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Status
             * @enum {string}
             */
            status: "verified" | "unsupported" | "ambiguous";
        };
        /**
         * DecisionIn
         * @description Karar gövdesi: revizyon (isteğe bağlı, eskimiş onayı yakalar).
         */
        DecisionIn: {
            /** Revision */
            revision?: string | null;
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
        /** DeepEvaluationOut */
        DeepEvaluationOut: {
            /** Candidate Context Revision */
            candidate_context_revision: string;
            /** Compensation */
            compensation?: {
                [key: string]: unknown;
            };
            /**
             * Confidence
             * @default 1
             */
            confidence: number;
            /** Created At */
            created_at: string;
            /** Evidence */
            evidence?: string[];
            /**
             * Is Stale
             * @default false
             */
            is_stale: boolean;
            /** Listing Fingerprint */
            listing_fingerprint: string;
            /** Location Fit */
            location_fit: string;
            /** Missing Requirements */
            missing_requirements?: string[];
            /** Model */
            model: string;
            /** Must Have */
            must_have?: components["schemas"]["RequirementAssessmentOut"][];
            /** Nice To Have */
            nice_to_have?: components["schemas"]["RequirementAssessmentOut"][];
            /** Opportunity Id */
            opportunity_id: string;
            /** Overall Assessment */
            overall_assessment: string;
            /** Partial Matches */
            partial_matches?: string[];
            /** Provider */
            provider: string;
            /** Recommended Next Steps */
            recommended_next_steps?: string[];
            /** Risks */
            risks?: string[];
            /** Role Fit */
            role_fit: string;
            /** Seniority Fit */
            seniority_fit: string;
            /** Sponsorship */
            sponsorship?: {
                [key: string]: unknown;
            };
            /** Stale Reasons */
            stale_reasons?: string[];
            /** Strengths */
            strengths?: string[];
            /** Unknowns */
            unknowns?: string[];
            /** Work Authorization */
            work_authorization?: {
                [key: string]: unknown;
            };
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
        /**
         * EnsureManagedNoteIn
         * @description Kanonik bilgi notu: kimliği verilen kalkın entity'sine bağlıdır.
         */
        EnsureManagedNoteIn: {
            /**
             * Forkos Id
             * Format: uuid
             */
            forkos_id: string;
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
        /**
         * EpisodeFinalizeIn
         * @description Oturum kapanışı. Transkript YOK; yalnız kimlik ve platform.
         */
        EpisodeFinalizeIn: {
            /**
             * Harness
             * @enum {string}
             */
            harness: "hermes" | "codex" | "claude";
            /**
             * Platform
             * @default unknown
             */
            platform: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Session Id */
            session_id: string;
        };
        /** EpisodeFinalizeOut */
        EpisodeFinalizeOut: {
            /** Degraded Reasons */
            degraded_reasons?: ("EPISODE_EXTRACTION_UNAVAILABLE" | "EPISODE_EXTRACTION_TIMEOUT" | "EPISODE_VALIDATION_FAILED" | "EPISODE_EMPTY" | "EPISODE_FINALIZE_DEGRADED" | "EPISODE_HANDOFF_UNAVAILABLE" | "EPISODE_SESSION_NOT_FOUND" | "EPISODE_INPUT_TRUNCATED" | "EPISODE_SEALED" | "SOURCE_BINDING_UNAVAILABLE" | "SOURCE_STALE" | "H5_UNAVAILABLE" | "LOCAL_COGNITION_UNAVAILABLE" | "VERBATIM_LEAKAGE" | "SCOPE_AMBIGUOUS" | "SECRET_LEAKAGE")[];
            /** Duplicate */
            duplicate: boolean;
            /** Episode Id */
            episode_id: number;
            /** Item Count */
            item_count: number;
            /** Scope Project */
            scope_project?: string | null;
            /** Sealed */
            sealed: boolean;
            /**
             * Sealed At
             * Format: date-time
             */
            sealed_at: string;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "sealed" | "sealed_degraded" | "sealed_empty";
            /** Turn Count */
            turn_count: number;
        };
        /**
         * EpisodeStatusOut
         * @description Metadata-only tanılama: ham konuşma YOK.
         */
        EpisodeStatusOut: {
            /** Available */
            available: boolean;
            /** Degraded Reasons */
            degraded_reasons?: ("EPISODE_EXTRACTION_UNAVAILABLE" | "EPISODE_EXTRACTION_TIMEOUT" | "EPISODE_VALIDATION_FAILED" | "EPISODE_EMPTY" | "EPISODE_FINALIZE_DEGRADED" | "EPISODE_HANDOFF_UNAVAILABLE" | "EPISODE_SESSION_NOT_FOUND" | "EPISODE_INPUT_TRUNCATED" | "EPISODE_SEALED" | "SOURCE_BINDING_UNAVAILABLE" | "SOURCE_STALE" | "H5_UNAVAILABLE" | "LOCAL_COGNITION_UNAVAILABLE" | "VERBATIM_LEAKAGE" | "SCOPE_AMBIGUOUS" | "SECRET_LEAKAGE")[];
            /**
             * Draft Episode Count
             * @default 0
             */
            draft_episode_count: number;
            /**
             * Last Episode Item Count
             * @default 0
             */
            last_episode_item_count: number;
            /** Last Scope Project */
            last_scope_project?: string | null;
            /** Last Sealed At */
            last_sealed_at?: string | null;
            /**
             * Recent Handoff Available
             * @default false
             */
            recent_handoff_available: boolean;
        };
        /**
         * EpisodeSupportRef
         * @description Bir ifadenin kanonik kökeni. Uydurma referans ÜRETİLMEZ.
         */
        EpisodeSupportRef: {
            /** Scope Project */
            scope_project?: string | null;
            /** Source Id */
            source_id: string;
            /** Source Type */
            source_type: string;
            /** Source Version */
            source_version?: string | null;
        };
        /**
         * EpisodeTurnIn
         * @description `post_llm_call` gözlemi. Ham transkript alanı KABUL ETMEZ.
         *
         *     `conversation_history` bu şemada YOKTUR ve `extra="forbid"` sayesinde
         *     gönderilirse 422 olur. `user_message`/`assistant_response` yalnız bu istek
         *     boyunca yaşayan GEÇİCİ girdilerdir; yanıt bunları geri döndürmez.
         */
        EpisodeTurnIn: {
            /** Assistant Response */
            assistant_response?: string | null;
            /**
             * Assistant Truncated
             * @default false
             */
            assistant_truncated: boolean;
            /**
             * Harness
             * @enum {string}
             */
            harness: "hermes" | "codex" | "claude";
            /**
             * Platform
             * @default unknown
             */
            platform: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Session Id */
            session_id: string;
            /** Turn Id */
            turn_id: string;
            /** User Message */
            user_message?: string | null;
            /**
             * User Truncated
             * @default false
             */
            user_truncated: boolean;
        };
        /**
         * EpisodeTurnOut
         * @description Tur gözleminin GÜVENLİ yanıtı: yalnız sayaç ve sınırlı kodlar.
         */
        EpisodeTurnOut: {
            /** Accepted */
            accepted: boolean;
            /** Degraded Reasons */
            degraded_reasons?: ("EPISODE_EXTRACTION_UNAVAILABLE" | "EPISODE_EXTRACTION_TIMEOUT" | "EPISODE_VALIDATION_FAILED" | "EPISODE_EMPTY" | "EPISODE_FINALIZE_DEGRADED" | "EPISODE_HANDOFF_UNAVAILABLE" | "EPISODE_SESSION_NOT_FOUND" | "EPISODE_INPUT_TRUNCATED" | "EPISODE_SEALED" | "SOURCE_BINDING_UNAVAILABLE" | "SOURCE_STALE" | "H5_UNAVAILABLE" | "LOCAL_COGNITION_UNAVAILABLE" | "VERBATIM_LEAKAGE" | "SCOPE_AMBIGUOUS" | "SECRET_LEAKAGE")[];
            /** Derived Item Count */
            derived_item_count: number;
            /** Duplicate */
            duplicate: boolean;
            /**
             * Latency Ms
             * @default 0
             */
            latency_ms: number;
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
        /**
         * FamilyOut
         * @description Bir Hermes fazinin (H0–H7) disa vurulan ozeti.
         */
        FamilyOut: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Summary */
            summary: string;
            /** Tool Count */
            tool_count: number;
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
            /** Cohort */
            cohort?: {
                [key: string]: number;
            };
            /**
             * Cohort Size
             * @default 0
             */
            cohort_size: number;
            /** Conversions */
            conversions: {
                [key: string]: number | null;
            };
            /**
             * Min Cohort Size
             * @default 10
             */
            min_cohort_size: number;
            /** Monthly Volume */
            monthly_volume?: components["schemas"]["FunnelVolumeRow"][];
            /** Rejection Reasons */
            rejection_reasons: {
                [key: string]: unknown;
            }[];
            /**
             * Sufficient
             * @default false
             */
            sufficient: boolean;
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
        /** GeneratedDocumentRefOut */
        GeneratedDocumentRefOut: {
            /**
             * Doc Type
             * @enum {string}
             */
            doc_type: "tailored_cv" | "cover_letter" | "pdf_cv";
            /** Document Id */
            document_id?: string | null;
            /** File Path */
            file_path?: string | null;
            /**
             * Mime
             * @default text/plain
             */
            mime: string;
            /** Title */
            title: string;
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
        /**
         * InterviewPrepOut
         * @description Mulakat hazirligi grubu: ilan + gorusmeler + maas tutarliligi.
         */
        InterviewPrepOut: {
            /** Interviews */
            interviews: components["schemas"]["InterviewOut"][];
            opportunity: components["schemas"]["OpportunityOut"];
            salary: components["schemas"]["SalaryConsistencyOut"];
        };
        /** IssueToTodoIn */
        IssueToTodoIn: {
            /** Number */
            number: number;
        };
        /** KnockoutAnswerOut */
        KnockoutAnswerOut: {
            /**
             * Confidence
             * @default 1
             */
            confidence: number;
            /** Evidence */
            evidence: string;
            /** Proposed Answer */
            proposed_answer: string;
            /** Question */
            question: string;
            /** Warning */
            warning?: string | null;
        };
        /** LifecycleEventIn */
        LifecycleEventIn: {
            /**
             * Event
             * @enum {string}
             */
            event: "session_start" | "turn_seen" | "session_finalize";
            /**
             * Harness
             * @enum {string}
             */
            harness: "hermes" | "codex" | "claude";
            /**
             * Platform
             * @default unknown
             */
            platform: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: 1;
            /** Session Id */
            session_id: string;
            /** Turn Id */
            turn_id?: string | null;
        };
        /** LifecycleEventOut */
        LifecycleEventOut: {
            /** Accepted */
            accepted: boolean;
            /** Duplicate */
            duplicate: boolean;
            /**
             * Event
             * @enum {string}
             */
            event: "session_start" | "turn_seen" | "session_finalize";
        };
        /** LifecycleStatusOut */
        LifecycleStatusOut: {
            /** Active Sessions */
            active_sessions: number;
            /** Available */
            available: boolean;
            /** Incomplete Session Count */
            incomplete_session_count: number;
            /** Last Event At */
            last_event_at: string | null;
            /** Last Finalized At */
            last_finalized_at: string | null;
            /** Last Harness */
            last_harness: string | null;
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
        /** ListingHealthOut */
        ListingHealthOut: {
            /** Health Score */
            health_score: number;
            /**
             * Jd Completeness
             * @enum {string}
             */
            jd_completeness: "complete" | "concise" | "stub";
            /**
             * Liveness Status
             * @enum {string}
             */
            liveness_status: "live" | "unchecked" | "at_risk" | "expired" | "uncertain";
            /**
             * Repost Frequency
             * @enum {string}
             */
            repost_frequency: "none" | "moderate" | "frequent";
            /**
             * Salary Transparency
             * @enum {string}
             */
            salary_transparency: "transparent" | "unclear" | "missing";
        };
        /**
         * LocalCognitionOut
         * @description H4 yerel bilis durumu. `reachable` yalnizca prob atildiysa doludur.
         */
        LocalCognitionOut: {
            /** Configured */
            configured: boolean;
            /** Detail */
            detail: string | null;
            /** Enabled */
            enabled: boolean;
            /**
             * Endpoint Class
             * @enum {string}
             */
            endpoint_class: "loopback" | "invalid";
            medium: components["schemas"]["SlotOut"];
            /** Provider */
            provider: string;
            /** Reachable */
            reachable: boolean | null;
            small: components["schemas"]["SlotOut"];
            /**
             * State
             * @enum {string}
             */
            state: "disabled" | "not_configured" | "provider_unreachable" | "model_missing" | "ready";
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
        /** ObservationLivenessOut */
        ObservationLivenessOut: {
            /** Liveness */
            liveness?: {
                [key: string]: unknown;
            } | null;
            /** Source */
            source: string;
            /** Source Status */
            source_status: string;
            /** Url */
            url: string;
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
        /** OperationalDeadline */
        OperationalDeadline: {
            /** Due At */
            due_at?: string | null;
            /**
             * Entity Type
             * @default todo
             */
            entity_type: string;
            /** Id */
            id: string;
            /** Module */
            module?: string | null;
            /** Priority */
            priority?: number | null;
            /** Remaining Days */
            remaining_days?: number | null;
            /** Title */
            title: string;
        };
        /** OperationalProject */
        OperationalProject: {
            /** Id */
            id: string;
            /** Last Activity At */
            last_activity_at?: string | null;
            /** Next Action */
            next_action?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** OperationalState */
        OperationalState: {
            /** Active Projects */
            active_projects?: components["schemas"]["OperationalProject"][];
            /**
             * Open Todos Count
             * @default 0
             */
            open_todos_count: number;
            /**
             * Pending Decisions Count
             * @default 0
             */
            pending_decisions_count: number;
            /** Pending Decisions Summary */
            pending_decisions_summary?: string[];
            /** Upcoming Deadlines */
            upcoming_deadlines?: components["schemas"]["OperationalDeadline"][];
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
            /**
             * Listing Fingerprint
             * @default
             */
            listing_fingerprint: string;
            /** Matches */
            matches?: components["schemas"]["EvaluationMatchOut"][];
            /** Notes */
            notes?: string | null;
            /**
             * Profile Fingerprint
             * @default
             */
            profile_fingerprint: string;
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
            listing_health?: components["schemas"]["ListingHealthOut"] | null;
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
        /** OpportunityJdExtractionResultOut */
        OpportunityJdExtractionResultOut: {
            /** Code */
            code?: string | null;
            /** Error */
            error?: string | null;
            /** Final Url */
            final_url?: string | null;
            /** Identity Status */
            identity_status?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Promoted */
            promoted: boolean;
            /** Promotion Reason */
            promotion_reason?: string | null;
            /** Reason */
            reason?: string | null;
            /** Requested Url */
            requested_url?: string | null;
            /** Text Length */
            text_length?: number | null;
            /** Title */
            title?: string | null;
        };
        /** OpportunityLivenessResultOut */
        OpportunityLivenessResultOut: {
            /** Observations */
            observations?: components["schemas"]["ObservationLivenessOut"][];
            /** Opportunity Id */
            opportunity_id: string;
            /** Source Status */
            source_status: string;
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
            /** Evaluation Stale Reason */
            evaluation_stale_reason?: string | null;
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
        /** PaidRecurringOut */
        PaidRecurringOut: {
            /** Id */
            id: number;
            /**
             * Paid At
             * Format: date-time
             */
            paid_at: string;
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
        /** PomodoroAnalytics */
        PomodoroAnalytics: {
            /** Completed */
            completed: number;
            /** Contexts */
            contexts: components["schemas"]["PomodoroContextStat"][];
            /** Daily */
            daily: components["schemas"]["PomodoroDailyPoint"][];
            /**
             * End Date
             * Format: date
             */
            end_date: string;
            /** Interrupted */
            interrupted: number;
            /** Minutes */
            minutes: number;
            /**
             * Range
             * @enum {string}
             */
            range: "week" | "month" | "all";
            /** Sessions */
            sessions: number;
            /**
             * Start Date
             * Format: date
             */
            start_date: string;
        };
        /** PomodoroContextStat */
        PomodoroContextStat: {
            /** Context Entity Id */
            context_entity_id: string | null;
            /** Context Type */
            context_type: string | null;
            /** Minutes */
            minutes: number;
            /** Sessions */
            sessions: number;
            /** Share */
            share: number;
            /** Title */
            title: string;
        };
        /** PomodoroDailyPoint */
        PomodoroDailyPoint: {
            /**
             * Date
             * Format: date
             */
            date: string;
            /** Interrupted */
            interrupted: number;
            /** Minutes */
            minutes: number;
            /** Sessions */
            sessions: number;
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
        /**
         * ProactivityConfigIn
         * @description Yalnizca BILINEN alanlar; bilinmeyen anahtar SESSIZCE DUSMEZ (§106).
         */
        ProactivityConfigIn: {
            /** Digest Time */
            digest_time?: string | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Focus Deferral Enabled */
            focus_deferral_enabled?: boolean | null;
            /** Quiet Hours End */
            quiet_hours_end?: string | null;
            /** Quiet Hours Start */
            quiet_hours_start?: string | null;
        };
        /** ProactivityFailureOut */
        ProactivityFailureOut: {
            /** At */
            at: string;
            /** Failure Code */
            failure_code: string | null;
            /** Rule Kind */
            rule_kind: string | null;
        };
        /**
         * ProactivityRuleIn
         * @description Kural ac/kapa ve esik ayari — kapali sema, serbest JSON degil.
         */
        ProactivityRuleIn: {
            /** Config */
            config?: {
                [key: string]: unknown;
            } | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Scope Entity Id */
            scope_entity_id?: string | null;
        };
        /** ProactivityRuleOut */
        ProactivityRuleOut: {
            /** Config */
            config: {
                [key: string]: unknown;
            };
            /** Enabled */
            enabled: boolean;
            /** Kind */
            kind: string;
            /** Logical Key */
            logical_key: string;
            /** Snoozed Until */
            snoozed_until?: string | null;
            /** Version */
            version: number;
        };
        /** ProactivityRunOut */
        ProactivityRunOut: {
            /** Delivered At */
            delivered_at?: string | null;
            /** Delivery Count */
            delivery_count: number;
            /** Failure Code */
            failure_code?: string | null;
            /** Id */
            id: number;
            /** Notification Id */
            notification_id?: number | null;
            /** Reason Codes */
            reason_codes?: string[];
            /** Rule Kind */
            rule_kind?: string | null;
            /** Snoozed Until */
            snoozed_until?: string | null;
            /** State */
            state: string;
            /** Subject Id */
            subject_id?: string | null;
            /** Subject Type */
            subject_type?: string | null;
            /** Triggered At */
            triggered_at: string;
            /** Why Now */
            why_now?: string | null;
        };
        /** ProactivityStatusOut */
        ProactivityStatusOut: {
            /** Digest Time */
            digest_time: string;
            /** Enabled */
            enabled: boolean;
            /** Focus Deferral Enabled */
            focus_deferral_enabled: boolean;
            /** Immediate Budget */
            immediate_budget: number;
            /** Immediate Surfaces Today */
            immediate_surfaces_today: number;
            /** Last Run At */
            last_run_at?: string | null;
            /** Pending Deferred */
            pending_deferred: number;
            /** Pending Digest */
            pending_digest: number;
            /** Quiet Hours End */
            quiet_hours_end: string;
            /** Quiet Hours Start */
            quiet_hours_start: string;
            /** Recent Failures */
            recent_failures: components["schemas"]["ProactivityFailureOut"][];
            /** Rules */
            rules: components["schemas"]["ProactivityRuleOut"][];
            /** Worker Heartbeat */
            worker_heartbeat?: {
                [key: string]: unknown;
            } | null;
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
            /**
             * Candidate Digest
             * @default
             */
            candidate_digest: string;
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
        /** RelatedSemanticCard */
        RelatedSemanticCard: {
            /** Card Id */
            card_id: string;
            /** Statement */
            statement: string;
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
        /** RequirementAssessmentOut */
        RequirementAssessmentOut: {
            /** Candidate Evidence Refs */
            candidate_evidence_refs?: string[];
            /**
             * Classification
             * @enum {string}
             */
            classification: "strong" | "partial" | "missing" | "unknown" | "not_applicable";
            /**
             * Confidence
             * @default 1
             */
            confidence: number;
            /** Listing Evidence Refs */
            listing_evidence_refs?: string[];
            /** Reason */
            reason: string;
            /** Requirement */
            requirement: string;
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
        /** ResolveAnswerIn */
        ResolveAnswerIn: {
            /** Answer */
            answer: string;
            /** Question */
            question: string;
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
        /** RespondIn */
        RespondIn: {
            /** Answers */
            answers?: {
                [key: string]: unknown;
            };
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
        /** ReviewNotePatch */
        ReviewNotePatch: {
            /** Note */
            note: string | null;
        };
        /** ReviewPreview */
        ReviewPreview: {
            /** Completed Todos */
            completed_todos: components["schemas"]["CompletedTodo"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "daily" | "weekly" | "monthly" | "yearly";
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
        /** SemanticCandidateConfirmIn */
        SemanticCandidateConfirmIn: {
            /** Expected Revision */
            expected_revision: string;
        };
        /** SemanticCandidateListResponse */
        SemanticCandidateListResponse: {
            /** Items */
            items: components["schemas"]["SemanticCandidateRead"][];
            /** Status Counts */
            status_counts?: {
                [key: string]: number;
            };
            /** Total */
            total: number;
        };
        /** SemanticCandidatePromoteIn */
        SemanticCandidatePromoteIn: {
            /** Expected Revision */
            expected_revision: string;
            /** Supersedes */
            supersedes?: string[] | null;
            /** Target Destination */
            target_destination?: ("operational" | "hot_memory" | "durable_vault" | "procedural_candidate" | "discard") | null;
        };
        /** SemanticCandidatePromoteOut */
        SemanticCandidatePromoteOut: {
            /** Card Id */
            card_id?: string | null;
            /** Destination */
            destination: string;
            /** Relative Path */
            relative_path?: string | null;
            /** Revision */
            revision: string;
            /** Status */
            status: string;
        };
        /** SemanticCandidateRead */
        SemanticCandidateRead: {
            /** Candidate Key */
            candidate_key: string;
            /** Conditions */
            conditions?: string[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Domains */
            domains?: string[];
            /** Evidence Refs */
            evidence_refs?: {
                [key: string]: unknown;
            }[];
            /** Exceptions */
            exceptions?: string[];
            /**
             * First Seen At
             * Format: date-time
             */
            first_seen_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "identity" | "preference" | "correction" | "constraint" | "goal" | "decision" | "lesson" | "project_knowledge" | "reference" | "commitment";
            /**
             * Last Seen At
             * Format: date-time
             */
            last_seen_at: string;
            /**
             * Observed At
             * Format: date-time
             */
            observed_at: string;
            /** Possible Related Card Ids */
            possible_related_card_ids?: string[];
            /** Possible Related Cards */
            possible_related_cards?: components["schemas"]["RelatedSemanticCard"][];
            /**
             * Primary Evidence Class
             * @enum {string}
             */
            primary_evidence_class: "explicit_user" | "canonical_source" | "episode_derived" | "model_derived";
            /** Rationale */
            rationale?: string | null;
            /**
             * Recurrence Count
             * @default 1
             */
            recurrence_count: number;
            /**
             * Remote Allowed
             * @default false
             */
            remote_allowed: boolean;
            /** Reviewed By */
            reviewed_by?: string | null;
            /** Revision */
            revision: string;
            /** Scope */
            scope: string;
            /** Scope Project */
            scope_project?: string | null;
            /**
             * Sensitivity
             * @default normal
             */
            sensitivity: string;
            /** Statement */
            statement: string;
            /**
             * Status
             * @enum {string}
             */
            status: "proposed" | "needs_review" | "ready" | "promoted" | "rejected" | "stale";
            /** Subject Key */
            subject_key?: string | null;
            /**
             * Suggested Destination
             * @enum {string}
             */
            suggested_destination: "operational" | "hot_memory" | "durable_vault" | "procedural_candidate" | "discard";
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Valid From */
            valid_from?: string | null;
            /** Valid To */
            valid_to?: string | null;
            /** Warnings */
            warnings?: string[];
        };
        /** SemanticCandidateRefreshIn */
        SemanticCandidateRefreshIn: {
            /**
             * Include Episodes
             * @default true
             */
            include_episodes: boolean;
            /**
             * Include Events
             * @default true
             */
            include_events: boolean;
            /**
             * Limit
             * @default 50
             */
            limit: number;
        };
        /** SemanticCandidateRefreshOut */
        SemanticCandidateRefreshOut: {
            /** Created Count */
            created_count: number;
            /** Total Candidates */
            total_candidates: number;
            /** Updated Count */
            updated_count: number;
        };
        /** SemanticCandidateRejectIn */
        SemanticCandidateRejectIn: {
            /** Expected Revision */
            expected_revision: string;
            /** Reason */
            reason?: string | null;
        };
        /** SemanticStatusOut */
        SemanticStatusOut: {
            /** Durable Card Count */
            durable_card_count: number;
            /** Needs Review Count */
            needs_review_count: number;
            /** Promoted Count */
            promoted_count: number;
            /** Proposed Count */
            proposed_count: number;
            /** Ready Count */
            ready_count: number;
            /** Rejected Count */
            rejected_count: number;
            /** Total Candidates */
            total_candidates: number;
        };
        /**
         * SessionHandoffItem
         * @description Tek epizodik ifade: tür, türetilmiş metin, epistemik sınıf ve köken.
         */
        SessionHandoffItem: {
            /**
             * Evidence Class
             * @enum {string}
             */
            evidence_class: "turn_derived" | "canonical_supported" | "observed_during_session";
            /** Evidence Digest */
            evidence_digest?: string | null;
            /**
             * Historical Support Stale
             * @default false
             */
            historical_support_stale: boolean;
            /**
             * Kind
             * @enum {string}
             */
            kind: "topic" | "outcome" | "open_thread" | "session_decision" | "next_focus" | "reference";
            /** Ordinal */
            ordinal: number;
            /** Source Role */
            source_role?: string | null;
            /** Support Refs */
            support_refs?: components["schemas"]["EpisodeSupportRef"][];
            /** Text */
            text: string;
            /** Turn Digest */
            turn_digest?: string | null;
        };
        /**
         * SessionHandoffV1
         * @description Önceki ilgili oturumun sınırlı, kaynağa bağlı epizodik devri.
         *
         *     Bu bir TARİHSEL özettir: güncel kanonik durum DEĞİLDİR, yetkilendirme
         *     DEĞİLDİR ve içindeki talimat benzeri metin güvenilmeyen veridir (§21/§26).
         */
        SessionHandoffV1: {
            /** Degraded Reasons */
            degraded_reasons?: ("EPISODE_EXTRACTION_UNAVAILABLE" | "EPISODE_EXTRACTION_TIMEOUT" | "EPISODE_VALIDATION_FAILED" | "EPISODE_EMPTY" | "EPISODE_FINALIZE_DEGRADED" | "EPISODE_HANDOFF_UNAVAILABLE" | "EPISODE_SESSION_NOT_FOUND" | "EPISODE_INPUT_TRUNCATED" | "EPISODE_SEALED" | "SOURCE_BINDING_UNAVAILABLE" | "SOURCE_STALE" | "H5_UNAVAILABLE" | "LOCAL_COGNITION_UNAVAILABLE" | "VERBATIM_LEAKAGE" | "SCOPE_AMBIGUOUS" | "SECRET_LEAKAGE")[];
            /** Episode Id */
            episode_id: number;
            /** Items */
            items?: components["schemas"]["SessionHandoffItem"][];
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: 1;
            /** Scope Project */
            scope_project?: string | null;
            /**
             * Sealed At
             * Format: date-time
             */
            sealed_at: string;
            /** Source Session Key */
            source_session_key: string;
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
         * SlotOut
         * @description Tek yerel model slotunun yapilandirma/kurulum durumu.
         */
        SlotOut: {
            /** Available */
            available: boolean;
            /** Configured */
            configured: boolean;
        };
        /**
         * SnoozeIn
         * @description Saat dilimli MUTLAK zaman; serbest metin cozumleme backend'de YOK (§108).
         */
        SnoozeIn: {
            /**
             * Until
             * Format: date-time
             */
            until: string;
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
            /**
             * Circuit Open
             * @default false
             */
            circuit_open: boolean;
            /**
             * Consecutive Failures
             * @default 0
             */
            consecutive_failures: number;
            /** Error */
            error?: string | null;
            /** Error Kind */
            error_kind?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Items Found */
            items_found: number;
            /** Retry At */
            retry_at?: string | null;
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
            /**
             * Partial Sources
             * @default 0
             */
            partial_sources: number;
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
            status: "queued" | "running" | "ok" | "partial" | "empty" | "error";
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
        /** TurnContextIn */
        TurnContextIn: {
            /**
             * Harness
             * @enum {string}
             */
            harness: "hermes" | "codex" | "claude";
            /**
             * Is First Turn
             * @default false
             */
            is_first_turn: boolean;
            /**
             * Platform
             * @default unknown
             */
            platform: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: 1;
            /** Scope Project */
            scope_project?: string | null;
            /** Session Id */
            session_id: string;
            /** Turn Id */
            turn_id?: string | null;
            /** User Message */
            user_message?: string | null;
        };
        /** TurnContextOut */
        TurnContextOut: {
            /** Degraded Reasons */
            degraded_reasons?: string[];
            handoff?: components["schemas"]["SessionHandoffV1"] | null;
            lifecycle: components["schemas"]["LifecycleEventOut"];
            packet?: components["schemas"]["BootstrapPacketV1"] | null;
            /** Rendered Context */
            rendered_context?: string | null;
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
        /** UriOut */
        UriOut: {
            /** Uri */
            uri: string;
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
        /**
         * VaultItem
         * @description Vault içinde forkOS tarafından yönetilen tek Markdown dosyası.
         *
         *     Yalnızca Vault köküne GÖRELİ yol döner; tam dosya sistemi yolu asla
         *     browser'a çıkmaz.
         */
        VaultItem: {
            /** Entity Type */
            entity_type?: string | null;
            /** Forkos Id */
            forkos_id: string;
            /** Forkos Type */
            forkos_type: string;
            /** Journal Day */
            journal_day?: string | null;
            /**
             * Mtime
             * @default 0
             */
            mtime: number;
            /** Note Kind */
            note_kind?: string | null;
            /** Open Uri */
            open_uri: string;
            /** Project Id */
            project_id?: string | null;
            /**
             * Relation Count
             * @default 0
             */
            relation_count: number;
            /** Relative Path */
            relative_path: string;
            /**
             * Size
             * @default 0
             */
            size: number;
            /** Source Bookmark Id */
            source_bookmark_id?: string | null;
            /** Title */
            title: string;
        };
        /** VaultStatus */
        VaultStatus: {
            /** Available */
            available: boolean;
            /** Configured */
            configured: boolean;
            /** Conflict Details */
            conflict_details?: {
                [key: string]: string[];
            };
            /** Conflicts */
            conflicts: number;
            /** Daily Uri */
            daily_uri?: string | null;
            /** Diagnostic */
            diagnostic?: string | null;
            /** Inbox Uri */
            inbox_uri?: string | null;
            /** Invalid Files */
            invalid_files?: string[];
            /** Managed Files */
            managed_files: number;
            /** Open Uri */
            open_uri?: string | null;
            /** Readable */
            readable: boolean;
            /** Vault Name */
            vault_name: string;
            /** Writable */
            writable: boolean;
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
            kind: "daily" | "weekly" | "monthly" | "yearly";
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
            kind: "daily" | "weekly" | "monthly" | "yearly";
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
                filter?: ("all" | "tasks" | "focus" | "learning" | "reading" | "career" | "system" | "alerts") | null;
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
                    "application/json": components["schemas"]["ActivityEventOut"][];
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
    continuity_status_api_agent_continuity_status_get: {
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
                    "application/json": components["schemas"]["ContinuityStatusOut"];
                };
            };
        };
    };
    episode_finalize_api_agent_episode_finalize_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EpisodeFinalizeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EpisodeFinalizeOut"];
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
    episode_status_api_agent_episode_status_get: {
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
                    "application/json": components["schemas"]["EpisodeStatusOut"];
                };
            };
        };
    };
    episode_turn_api_agent_episode_turn_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EpisodeTurnIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EpisodeTurnOut"];
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
    lifecycle_event_api_agent_lifecycle_event_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LifecycleEventIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LifecycleEventOut"];
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
    lifecycle_status_api_agent_lifecycle_status_get: {
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
                    "application/json": components["schemas"]["LifecycleStatusOut"];
                };
            };
        };
    };
    lifecycle_turn_api_agent_lifecycle_turn_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TurnContextIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TurnContextOut"];
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
    list_candidates_api_agent_semantic_candidates_get: {
        parameters: {
            query?: {
                status?: string | null;
                kind?: string | null;
                destination?: string | null;
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
                    "application/json": components["schemas"]["SemanticCandidateListResponse"];
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
    get_candidate_api_agent_semantic_candidates__candidate_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: string;
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
                    "application/json": components["schemas"]["SemanticCandidateRead"];
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
    confirm_candidate_api_agent_semantic_candidates__candidate_id__confirm_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SemanticCandidateConfirmIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SemanticCandidateRead"];
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
    promote_candidate_api_agent_semantic_candidates__candidate_id__promote_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SemanticCandidatePromoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SemanticCandidatePromoteOut"];
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
    reject_candidate_api_agent_semantic_candidates__candidate_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                candidate_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SemanticCandidateRejectIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SemanticCandidateRead"];
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
    refresh_candidates_api_agent_semantic_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SemanticCandidateRefreshIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SemanticCandidateRefreshOut"];
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
    get_status_api_agent_semantic_status_get: {
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
                    "application/json": components["schemas"]["SemanticStatusOut"];
                };
            };
        };
    };
    agent_status_api_agent_status_get: {
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
                    "application/json": components["schemas"]["AgentStatusOut"];
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
                    "application/json": components["schemas"]["ApplicationListOut"];
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
                state?: string | null;
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
    create_source_note_api_bookmarks__bookmark_id__source_note_post: {
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
                "application/json": components["schemas"]["CreateSourceNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VaultItem"];
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
    career_cover_letters_api_career_cover_letters_get: {
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
                    "application/json": components["schemas"]["CoverLetterOut"][];
                };
            };
        };
    };
    career_interview_prep_api_career_interview_prep_get: {
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
                    "application/json": components["schemas"]["InterviewPrepOut"][];
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
    list_plans_api_execution_plans_get: {
        parameters: {
            query?: {
                states?: string | null;
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
                    "application/json": {
                        [key: string]: unknown;
                    }[];
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
    get_plan_api_execution_plans__plan_row_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
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
                    "application/json": {
                        [key: string]: unknown;
                    };
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
    approve_api_execution_plans__plan_row_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionIn"];
            };
        };
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
    cancel_api_execution_plans__plan_row_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionIn"];
            };
        };
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
    execute_api_execution_plans__plan_row_id__execute_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionIn"];
            };
        };
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
    recover_api_execution_plans__plan_row_id__recover_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionIn"];
            };
        };
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
    reject_api_execution_plans__plan_row_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionIn"];
            };
        };
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
    respond_api_execution_plans__plan_row_id__respond_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_row_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RespondIn"];
            };
        };
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
    capture_note_api_obsidian_capture_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaptureNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VaultItem"];
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
    ensure_item_api_obsidian_ensure_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EnsureManagedNoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VaultItem"];
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
    refresh_index_api_obsidian_index_refresh_post: {
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
                    "application/json": components["schemas"]["VaultStatus"];
                };
            };
        };
    };
    get_item_api_obsidian_items__forkos_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                forkos_id: string;
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
                    "application/json": components["schemas"]["VaultItem"];
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
    get_status_api_obsidian_status_get: {
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
                    "application/json": components["schemas"]["VaultStatus"];
                };
            };
        };
    };
    search_uri_for_api_obsidian_uri_search_get: {
        parameters: {
            query: {
                q: string;
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
                    "application/json": components["schemas"]["UriOut"];
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
                score_state?: ("any" | "computed" | "uncomputed") | null;
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
    get_opportunity_application_package_api_opportunities__id__application_package_get: {
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
                    "application/json": components["schemas"]["ApplicationPackageOut"];
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
    resolve_application_package_answer_api_opportunities__id__application_package_resolve_answer_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResolveAnswerIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationPackageOut"];
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
    evaluate_opportunity_deep_api_opportunities__id__deep_evaluate_post: {
        parameters: {
            query?: {
                force?: boolean;
            };
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
                    "application/json": components["schemas"]["DeepEvaluationOut"];
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
    get_opportunity_deep_evaluation_api_opportunities__id__deep_evaluation_get: {
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
                    "application/json": components["schemas"]["DeepEvaluationOut"];
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
    extract_opportunity_jd_api_opportunities__id__extract_jd_post: {
        parameters: {
            query?: {
                force?: boolean;
            };
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
                    "application/json": components["schemas"]["OpportunityJdExtractionResultOut"];
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
    check_opportunity_liveness_api_opportunities__id__liveness_post: {
        parameters: {
            query?: {
                force?: boolean;
            };
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
                    "application/json": components["schemas"]["OpportunityLivenessResultOut"];
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
    prepare_opportunity_application_package_api_opportunities__id__prepare_package_post: {
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
                    "application/json": components["schemas"]["ApplicationPackageOut"];
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
                    "application/json": components["schemas"]["VaultItem"];
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
    analytics_api_pomodoro_analytics_get: {
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
                    "application/json": components["schemas"]["PomodoroAnalytics"];
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
    put_config_api_proactivity_config_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProactivityConfigIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProactivityStatusOut"];
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
    get_history_api_proactivity_history_get: {
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
                    "application/json": components["schemas"]["ProactivityRunOut"][];
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
    get_rules_api_proactivity_rules_get: {
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
                    "application/json": components["schemas"]["ProactivityRuleOut"][];
                };
            };
        };
    };
    put_rule_api_proactivity_rules__kind__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProactivityRuleIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProactivityRuleOut"];
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
    snooze_rule_api_proactivity_rules__kind__snooze_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SnoozeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProactivityRuleOut"][];
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
    snooze_run_api_proactivity_runs__run_id__snooze_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SnoozeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProactivityRunOut"][];
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
    unsnooze_run_api_proactivity_runs__run_id__snooze_delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: number;
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
                    "application/json": components["schemas"]["ProactivityRunOut"][];
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
    get_status_api_proactivity_status_get: {
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
                    "application/json": components["schemas"]["ProactivityStatusOut"];
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
    open_project_journal_in_obsidian_api_projects__project_id__journal__day__obsidian_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
                day: string;
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
                    "application/json": components["schemas"]["VaultItem"];
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
    recurring_history_api_recurring_payments_history_get: {
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
                    "application/json": components["schemas"]["PaidRecurringOut"][];
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
    patch_review_note_api_reviews__review_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewNotePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
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
    automation_state_api_system_automation_get: {
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
    set_automation_profile_api_system_automation_profile_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AutomationProfileIn"];
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
    career_ops_doctor_api_system_career_ops_doctor_get: {
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
    system_storage_api_system_storage_get: {
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
