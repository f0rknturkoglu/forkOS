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
         * @description Google Calendar token'ini siler; yeni senkron icin yeniden baglanmak gerekir.
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
         * @description Son yerel yedek ve yedek kapsami -- tek bakisla.
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
    "/api/career/insights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Career Insights */
        get: operations["career_insights_api_career_insights_get"];
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
    "/api/career/interviews/{id}/debrief": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Debrief Interview Intelligence */
        post: operations["debrief_interview_intelligence_api_career_interviews__id__debrief_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/interviews/{id}/intelligence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Interview Intelligence */
        get: operations["read_interview_intelligence_api_career_interviews__id__intelligence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/interviews/{id}/practice": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Practice Interview Intelligence */
        post: operations["practice_interview_intelligence_api_career_interviews__id__practice_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/interviews/{id}/prepare": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Prepare Interview Intelligence */
        post: operations["prepare_interview_intelligence_api_career_interviews__id__prepare_post"];
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
    "/api/career/strategy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Career Strategy
         * @description Read-only career briefing over canonical evidence and commitments.
         */
        get: operations["career_strategy_api_career_strategy_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/strategy/proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Career Strategy Proposals */
        get: operations["career_strategy_proposals_api_career_strategy_proposals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/strategy/proposals/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh Career Strategy Proposals
         * @description Persist bounded proposals; no Goal/Learning/Todo is created here.
         */
        post: operations["refresh_career_strategy_proposals_api_career_strategy_proposals_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/strategy/proposals/{proposal_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Career Strategy Proposal */
        post: operations["approve_career_strategy_proposal_api_career_strategy_proposals__proposal_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/career/strategy/proposals/{proposal_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject Career Strategy Proposal */
        post: operations["reject_career_strategy_proposal_api_career_strategy_proposals__proposal_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/api/execution/planning": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Prepare Schedule */
        post: operations["prepare_schedule_api_execution_planning_post"];
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
    "/api/flashcard/catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Shared Decks */
        get: operations["shared_decks_api_flashcard_catalog_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/catalog/{shared_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Preview Shared Deck */
        get: operations["preview_shared_deck_api_flashcard_catalog__shared_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/flashcard/catalog/{shared_id}/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Shared Deck */
        post: operations["import_shared_deck_api_flashcard_catalog__shared_id__import_post"];
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
    "/api/goal-milestones/{milestone_id}": {
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
        /** Update Milestone */
        patch: operations["update_milestone_api_goal_milestones__milestone_id__patch"];
        trace?: never;
    };
    "/api/goals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Goals */
        get: operations["goals_api_goals_get"];
        put?: never;
        /** Create Goal */
        post: operations["create_goal_api_goals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/roadmap-nodes/{node_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Roadmap Owner */
        get: operations["roadmap_owner_api_goals_roadmap_nodes__node_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/strategy/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Strategy History */
        get: operations["strategy_history_api_goals_strategy_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/strategy/overview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Strategy Overview */
        get: operations["strategy_overview_api_goals_strategy_overview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/strategy/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Plan Create */
        post: operations["plan_create_api_goals_strategy_plans_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/strategy/plans/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Plan Update */
        put: operations["plan_update_api_goals_strategy_plans__plan_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/strategy/plans/{plan_id}/pillars": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pillar Create */
        post: operations["pillar_create_api_goals_strategy_plans__plan_id__pillars_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/strategy/plans/{plan_id}/pillars/{pillar_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Pillar Update */
        put: operations["pillar_update_api_goals_strategy_plans__plan_id__pillars__pillar_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/consent": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Consent */
        put: operations["consent_api_goals_studio_consent_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/context": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Context */
        post: operations["context_api_goals_studio_context_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start */
        post: operations["start_api_goals_studio_sessions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read */
        get: operations["read_api_goals_studio_sessions__session_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions/{session_id}/decision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide */
        post: operations["decide_api_goals_studio_sessions__session_id__decision_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions/{session_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Events */
        get: operations["events_api_goals_studio_sessions__session_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions/{session_id}/proposal": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Revise */
        put: operations["revise_api_goals_studio_sessions__session_id__proposal_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions/{session_id}/stop": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Stop */
        post: operations["stop_api_goals_studio_sessions__session_id__stop_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/sessions/{session_id}/turns": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Turn */
        post: operations["turn_api_goals_studio_sessions__session_id__turns_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/studio/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Status */
        get: operations["status_api_goals_studio_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Goal */
        get: operations["goal_api_goals__goal_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Goal */
        patch: operations["update_goal_api_goals__goal_id__patch"];
        trace?: never;
    };
    "/api/goals/{goal_id}/actions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Goal Action */
        post: operations["add_goal_action_api_goals__goal_id__actions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}/conversation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Living Conversation */
        get: operations["living_conversation_api_goals__goal_id__conversation_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}/key-results": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Kr Create */
        post: operations["kr_create_api_goals__goal_id__key_results_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}/key-results/{kr_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Kr Update */
        put: operations["kr_update_api_goals__goal_id__key_results__kr_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}/milestones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Milestone */
        post: operations["add_milestone_api_goals__goal_id__milestones_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}/roadmap": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Roadmap Read */
        get: operations["roadmap_read_api_goals__goal_id__roadmap_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goals/{goal_id}/workspace": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Living Workspace */
        get: operations["living_workspace_api_goals__goal_id__workspace_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
    "/api/news/huggingface-papers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Huggingface Papers */
        get: operations["huggingface_papers_api_news_huggingface_papers_get"];
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
         *     Yalnız kaydedilmiş opt-in kaynak listesi kullanılır.
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
         *     Kimliği client_uuid veya sunucu üretir; forkOS veritabanında not kaydı OLUŞMAZ. İlişki
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
    "/api/opportunities/{id}/application-package/review-cover-letter": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Review Application Package Cover Letter
         * @description Ön yazının açık kullanıcı incelemesini kaydet; başvuru göndermez.
         */
        post: operations["review_application_package_cover_letter_api_opportunities__id__application_package_review_cover_letter_post"];
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
        /** Update */
        put: operations["update_api_pomodoro__pomo_id__put"];
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
    "/api/projects/{project_id}/resources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project Resources */
        get: operations["project_resources_api_projects__project_id__resources_get"];
        put?: never;
        /** Add Project Resource */
        post: operations["add_project_resource_api_projects__project_id__resources_post"];
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
         * @description Acknowledge completion before the UI invalidates RSS data.
         *
         *     The existing bounded per-feed fetch records source_run health. A successful
         *     response means the refresh finished, not that every source is healthy.
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
    "/api/sources/career-ops/providers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Career Ops Providers
         * @description Pinned provider registry and actual configured scan target coverage.
         */
        get: operations["career_ops_providers_api_sources_career_ops_providers_get"];
        put?: never;
        post?: never;
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
    "/api/sources/forkjob-core/config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Forkjob Core Config */
        get: operations["forkjob_core_config_api_sources_forkjob_core_config_get"];
        /**
         * Forkjob Core Config Update
         * @description Uyum profili ve dengeler. config.yaml a yazilir ve SICAK yuklenir.
         *
         *     Yeni skorlar bir sonraki senkron turunda gecerli olur (forkjob_port.SCORING
         *     aninda guncellenir).
         */
        put: operations["forkjob_core_config_update_api_sources_forkjob_core_config_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/forkjob-core/env": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Forkjob Core Env
         * @description LinkedIn direct/proxy ayarlarinin gercek durumu.
         *
         *     `allow_direct` bir guvenlik anahtaridir: yalnizca ortam degiskeni acikca
         *     acarsa true olur (bkz. `env_flag`). `linkedin_allow_direct` kanonik
         *     alandir; yanlis yazilmis `linkein_allow_direct` alani eski istemciler
         *     icin gecici uyumluluk takma adi olarak korunur.
         */
        get: operations["forkjob_core_env_api_sources_forkjob_core_env_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/sources/forkjob-core/linkedin-profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Forkjob Core Linkedin Profiles */
        get: operations["forkjob_core_linkedin_profiles_api_sources_forkjob_core_linkedin_profiles_get"];
        /**
         * Forkjob Core Linkedin Profiles Save
         * @description Kullanici LinkedIn arama profillerinin tamami -- atomik YAML yazimi.
         */
        put: operations["forkjob_core_linkedin_profiles_save_api_sources_forkjob_core_linkedin_profiles_put"];
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
         *     calistirilabilir kaynaklarini kosar. Her durumda critical -> normal -> slow_optin sirasi
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
    "/api/system/experience": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Experience */
        get: operations["get_experience_api_system_experience_get"];
        /** Put Experience */
        put: operations["put_experience_api_system_experience_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/experience/repair": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Repair Experience */
        post: operations["repair_experience_api_system_experience_repair_post"];
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
        /** AcceptedRevision */
        AcceptedRevision: {
            /** Assumptions */
            assumptions: string[];
            constraints: components["schemas"]["PlanningConstraints"] | null;
            /** Fingerprint */
            fingerprint: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
        };
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
        /** ActivityWindow */
        ActivityWindow: {
            /** Completed Todos */
            completed_todos: number;
            /** Count */
            count: number;
            /** Evidence Ids */
            evidence_ids: string[];
            /** Truncated */
            truncated: boolean;
        };
        /** AgendaRow */
        AgendaRow: {
            /** Action */
            action?: ("complete_todo" | "mark_rss_read") | null;
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
            kind: "calendar" | "todo" | "rss" | "opportunity" | "interview" | "study" | "flashcard" | "pomodoro";
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
        /** Aggregate */
        Aggregate: {
            /** Active Objectives */
            active_objectives: number;
            /** Confidence */
            confidence: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Measurable Objectives */
            measurable_objectives: number;
            /**
             * Method
             * @default weighted-active-objectives-pillar-weight-v1; minimum 80% measurable coverage
             */
            method: string;
            /** Progress Percent */
            progress_percent: number | null;
        };
        /** Alignment */
        Alignment: {
            /** Eligible Count */
            eligible_count: number;
            /**
             * End At
             * Format: date-time
             */
            end_at: string;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Linked Count */
            linked_count: number;
            /**
             * Method
             * @default meaningful-events-links-v1
             */
            method: string;
            /** Objectives */
            objectives: components["schemas"]["Allocation"][];
            /** Percent */
            percent: number | null;
            /** Pillars */
            pillars: components["schemas"]["Allocation"][];
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
            /** Unaligned Count */
            unaligned_count: number;
            /** Warnings */
            warnings: components["schemas"]["Reason"][];
            /**
             * Window Days
             * @enum {integer}
             */
            window_days: 7 | 30 | 90;
        };
        /** Allocation */
        Allocation: {
            /** Count */
            count: string;
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /** Share Percent */
            share_percent: number;
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
            cover_letter_review?: components["schemas"]["PackageCoverLetterReviewOut"];
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
        /** AreaData */
        AreaData: {
            /** Title */
            title: string;
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
        /** AssistanceSummary */
        AssistanceSummary: {
            coverage?: components["schemas"]["Coverage"] | null;
            /** Facts */
            facts?: components["schemas"]["ContextFact"][];
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            /** Links */
            links?: components["schemas"]["ContextLink"][];
            /** Memory Candidates */
            memory_candidates?: components["schemas"]["SemanticCandidateRead"][];
            /** Sources */
            sources?: components["schemas"]["SourceRef"][];
            /** Strategy Snapshot */
            strategy_snapshot?: {
                [key: string]: unknown;
            } | null;
            /** Title */
            title: string;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
            /** Warnings */
            warnings?: string[];
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
            /** Client Uuid */
            client_uuid?: string | null;
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
         * @description Hızlı yakalama: yeni bilgi notu; client_uuid varsa tekrar güvenli kimlik.
         */
        CaptureNoteIn: {
            /** Body */
            body: string;
            /** Client Uuid */
            client_uuid?: string | null;
            /** Folder */
            folder?: string | null;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /** Relate To */
            relate_to?: string | null;
            /** Source Url */
            source_url?: string | null;
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
        /** CareerAnalyticsSnapshot */
        CareerAnalyticsSnapshot: {
            /** Briefing */
            briefing: {
                [key: string]: string;
            };
            /** Calibration */
            calibration: {
                [key: string]: unknown;
            }[];
            /**
             * Candidate Context Revision
             * @default
             */
            candidate_context_revision: string;
            /** Cohorts */
            cohorts: components["schemas"]["Cohort"][];
            /** Confidence Notes */
            confidence_notes: string[];
            /** Conversions */
            conversions: {
                [key: string]: components["schemas"]["Conversion"];
            };
            /** Durations */
            durations: {
                [key: string]: {
                    [key: string]: number | null;
                };
            };
            /** Evaluated Population */
            evaluated_population: number;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Fingerprint */
            fingerprint: string;
            /** Funnel */
            funnel: {
                [key: string]: number;
            };
            /** Generated At */
            generated_at: string;
            /** Geography */
            geography: components["schemas"]["Cohort"][];
            /** Lineage */
            lineage: {
                [key: string]: unknown;
            }[];
            /** Minimum Sample */
            minimum_sample: number;
            /** Period */
            period: {
                [key: string]: string;
            };
            /** Population */
            population: number;
            /** Rejection Patterns */
            rejection_patterns: {
                [key: string]: unknown;
            }[];
            /** Skill Gaps */
            skill_gaps: components["schemas"]["SkillGapSignal"][];
            /** Source Performance */
            source_performance: components["schemas"]["Cohort"][];
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
        /** CareerContext */
        CareerContext: {
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "career";
        };
        /** CareerGoalReviewProgress */
        CareerGoalReviewProgress: {
            /** Completed Milestones */
            completed_milestones: number;
            /**
             * Goal Id
             * Format: uuid
             */
            goal_id: string;
            /** Milestone Count */
            milestone_count: number;
            /** Progress Percent */
            progress_percent: number | null;
            /** Title */
            title: string;
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
        /** CareerStrategySnapshot */
        CareerStrategySnapshot: {
            /** Alternatives */
            alternatives: components["schemas"]["RecommendedAction"][];
            /** Audit */
            audit: string[];
            /** Evaluated Population */
            evaluated_population: number;
            /** Evidence Revision */
            evidence_revision: string;
            /** Existing Goals */
            existing_goals: components["schemas"]["StrategicSignal"][];
            /** Generated At */
            generated_at: string;
            /** Goal Progress */
            goal_progress: components["schemas"]["GoalProgress"][];
            /** Period */
            period: {
                [key: string]: string;
            };
            /** Population */
            population: number;
            primary_action: components["schemas"]["RecommendedAction"] | null;
            /** Project Progress */
            project_progress: components["schemas"]["ProjectMilestoneProgress"][];
            /** Signals */
            signals: components["schemas"]["StrategicSignal"][];
            /** Summary */
            summary: string;
            /** Uncertainties */
            uncertainties: string[];
            /** What Changed */
            what_changed: string;
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
        /** Cohort */
        Cohort: {
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Dimension */
            dimension: string;
            interview_conversion: components["schemas"]["Conversion"];
            /** Sample Size */
            sample_size: number;
            /** Status */
            status: string;
            /** Value */
            value: string;
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
        /** ConnectRecord */
        ConnectRecord: {
            data: components["schemas"]["LinkData"];
            /** From Ref */
            from_ref: string;
            /** Key */
            key: string;
            /** To Ref */
            to_ref: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "record.link";
        };
        /** ContextFact */
        ContextFact: {
            /**
             * Status
             * @default fact
             * @enum {string}
             */
            status: "fact" | "candidate" | "missing";
            /** Support Refs */
            support_refs?: string[];
            /** Text */
            text: string;
            /** Timestamp */
            timestamp?: string | null;
        };
        /** ContextLink */
        ContextLink: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Route */
            route: string;
            /**
             * Schedulable
             * @default false
             */
            schedulable: boolean;
            /** Title */
            title: string;
            /** Type */
            type: string;
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
        /** Conversion */
        Conversion: {
            /** Denominator */
            denominator: number;
            /** Numerator */
            numerator: number;
            /** Rate */
            rate: number | null;
            /** Status */
            status: string;
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
         * Coverage
         * @description Dönem kapsamı ve dürüstlük bayrakları (§47/§97).
         */
        Coverage: {
            /**
             * Comparable
             * @description Tam dönemlerle sayısal karşılaştırma yapılabilir mi.
             * @default true
             */
            comparable: boolean;
            /** Days */
            days: number;
            /**
             * Partial
             * @description Dönem henüz tamamlanmadı.
             * @default false
             */
            partial: boolean;
            /**
             * Period End
             * @description ISO-8601, saat dilimli (hariç).
             */
            period_end: string;
            /**
             * Period Start
             * @description ISO-8601, saat dilimli.
             */
            period_start: string;
            /** Reference Date */
            reference_date?: string | null;
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
        /** DebriefIn */
        DebriefIn: {
            /**
             * Candidate Notes
             * @default
             */
            candidate_notes: string;
            /** Employer Feedback */
            employer_feedback?: string | null;
            /** Follow Up Items */
            follow_up_items?: string[];
            /** New Story Proposals */
            new_story_proposals?: components["schemas"]["StoryProposal"][];
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Outcome If Known */
            outcome_if_known?: string | null;
            /** Perceived Gaps */
            perceived_gaps?: string[];
            /** Perceived Strengths */
            perceived_strengths?: string[];
            /** Questions Asked */
            questions_asked?: string[];
            /** Story Updates */
            story_updates?: string[];
            /** Topics */
            topics?: string[];
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
        /** EditGoal */
        "EditGoal-Input": {
            data: components["schemas"]["StudioGoalPatch-Input"];
            /** Key */
            key: string;
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "goal.update";
        };
        /** EditGoal */
        "EditGoal-Output": {
            data: components["schemas"]["StudioGoalPatch-Output"];
            /** Key */
            key: string;
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "goal.update";
        };
        /** EditMilestone */
        EditMilestone: {
            data: components["schemas"]["StudioMilestonePatch"];
            /** Key */
            key: string;
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "milestone.update";
        };
        /** EditNode */
        "EditNode-Input": {
            data: components["schemas"]["NodeData-Input"];
            /** Depends On */
            depends_on?: string[] | null;
            /**
             * Detached
             * @default false
             */
            detached: boolean;
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "roadmap.update";
        };
        /** EditNode */
        "EditNode-Output": {
            data: components["schemas"]["NodeData-Output"];
            /** Depends On */
            depends_on?: string[] | null;
            /**
             * Detached
             * @default false
             */
            detached: boolean;
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "roadmap.update";
        };
        /** EditTask */
        EditTask: {
            data: components["schemas"]["TaskPatch"];
            /** Key */
            key: string;
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "todo.update";
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
        /** ExperienceOut */
        ExperienceOut: {
            /** Canonical Actions */
            canonical_actions?: {
                [key: string]: number;
            };
            /** Counts */
            counts: {
                [key: string]: number;
            };
            feed?: components["schemas"]["FeedPreferences"];
            /** First Run */
            first_run: boolean;
            /** Invalid Feed Ids */
            invalid_feed_ids?: string[];
            onboarding?: components["schemas"]["OnboardingState"];
            /** Revision */
            revision: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Version
             * @default 1
             * @constant
             */
            version: 1;
            /** Warnings */
            warnings?: string[];
        };
        /** ExperienceRepairIn */
        ExperienceRepairIn: {
            /** Revision */
            revision: string;
        };
        /** ExperienceUpdate */
        ExperienceUpdate: {
            feed?: components["schemas"]["FeedPreferences"] | null;
            onboarding?: components["schemas"]["OnboardingState"] | null;
            /** Revision */
            revision: string;
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
        /** FeedBundle */
        FeedBundle: {
            /** Channels */
            channels?: ("hn" | "gh" | "hf" | "reddit" | "rss")[];
            /** Feed Ids */
            feed_ids?: string[];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
        };
        /** FeedIn */
        FeedIn: {
            /** Category */
            category?: string | null;
            /**
             * Probe
             * @default true
             */
            probe: boolean;
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
        /** FeedPreferences */
        FeedPreferences: {
            /** Bundles */
            bundles?: components["schemas"]["FeedBundle"][];
            /** Providers */
            providers?: ("hn" | "gh" | "hf" | "reddit")[];
            /**
             * Rss Enabled
             * @default false
             */
            rss_enabled: boolean;
            /** Subreddits */
            subreddits?: string[];
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
        /** Finding */
        Finding: {
            /** Code */
            code: string;
            /** Entity Refs */
            entity_refs: string[];
            /** Evidence Refs */
            evidence_refs: string[];
            /** Observed Facts */
            observed_facts: string;
            /**
             * Severity
             * @default warning
             * @enum {string}
             */
            severity: "info" | "warning";
            /**
             * Window End
             * Format: date-time
             */
            window_end: string;
            /**
             * Window Start
             * Format: date-time
             */
            window_start: string;
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
        /** ForkjobCoreEnvOut */
        ForkjobCoreEnvOut: {
            /** Linkedin Allow Direct */
            linkedin_allow_direct: boolean;
            /** Linkein Allow Direct */
            linkein_allow_direct?: boolean | null;
            /** Proxies File */
            proxies_file: string;
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
            /** Opportunity Id */
            opportunity_id?: string | null;
            /** Parent Document Id */
            parent_document_id?: string | null;
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
        /** GoalActionIn */
        GoalActionIn: {
            /** Area Id */
            area_id?: string | null;
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "todo" | "study_topic";
            /**
             * Milestone Id
             * Format: uuid
             */
            milestone_id: string;
            /** New Area Title */
            new_area_title?: string | null;
            /** Plan Day */
            plan_day?: string | null;
        };
        /** GoalActionOut */
        GoalActionOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "todo" | "study_topic";
        };
        /** GoalContext */
        GoalContext: {
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "goal";
        };
        /** GoalContextSnapshot */
        GoalContextSnapshot: {
            /** Accepted Revisions */
            accepted_revisions: components["schemas"]["AcceptedRevision"][];
            /** Activity Windows */
            activity_windows: {
                [key: string]: components["schemas"]["ActivityWindow"];
            };
            /**
             * Collected At
             * Format: date-time
             */
            collected_at: string;
            goal: components["schemas"]["GoalIdentity"];
            /** Learning */
            learning: components["schemas"]["SnapshotTopic"][];
            outcome: components["schemas"]["SnapshotOutcome"];
            /** Planned Slots */
            planned_slots: components["schemas"]["SnapshotSlot"][];
            /** Projects */
            projects: components["schemas"]["SnapshotProject"][];
            recorded_constraints?: components["schemas"]["PlanningConstraints"] | null;
            /** Resources */
            resources: components["schemas"]["SnapshotResource"][];
            /** Reviews */
            reviews: components["schemas"]["SnapshotReview"][];
            roadmap: components["schemas"]["SnapshotRoadmap"];
            /**
             * Schema Version
             * @constant
             */
            schema_version: 2;
            /** Scope */
            scope: string;
            /** Todos */
            todos: components["schemas"]["SnapshotTask"][];
            /** Truncated */
            truncated: boolean;
            /** Warnings */
            warnings: string[];
        };
        /** GoalIdentity */
        GoalIdentity: {
            /** Description */
            description: string;
            /** Horizon */
            horizon: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Parent Goal Id */
            parent_goal_id: string | null;
            /** Target At */
            target_at: string | null;
            /** Title */
            title: string;
        };
        /** GoalIn */
        GoalIn: {
            /** Description */
            description?: string | null;
            /**
             * Horizon
             * @default quarter
             * @enum {string}
             */
            horizon: "short_term" | "quarter" | "year" | "long_term";
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
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
            /** Source Memory Id */
            source_memory_id?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at?: string | null;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** GoalMilestoneIn */
        GoalMilestoneIn: {
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
        /** GoalMilestoneOut */
        GoalMilestoneOut: {
            /** Completed At */
            completed_at: string | null;
            /** Due At */
            due_at: string | null;
            /**
             * Goal Id
             * Format: uuid
             */
            goal_id: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Position */
            position: number;
            /** Title */
            title: string;
        };
        /** GoalMilestonePatch */
        GoalMilestonePatch: {
            /** Completed */
            completed?: boolean | null;
            /** Due At */
            due_at?: string | null;
            /** Position */
            position?: number | null;
            /** Title */
            title?: string | null;
        };
        /** GoalOut */
        GoalOut: {
            /** Completed Milestones */
            completed_milestones: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Description */
            description: string | null;
            /**
             * Horizon
             * @enum {string}
             */
            horizon: "short_term" | "quarter" | "year" | "long_term";
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Milestone Count */
            milestone_count: number;
            /** Milestone Progress Percent */
            milestone_progress_percent?: number | null;
            /** Milestones */
            milestones: components["schemas"]["GoalMilestoneOut"][];
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
            /** Position */
            position: number;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Progress Percent */
            progress_percent: number | null;
            /** Source Memory Id */
            source_memory_id: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at: string | null;
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** GoalPatch */
        GoalPatch: {
            /** Description */
            description?: string | null;
            /** Horizon */
            horizon?: ("short_term" | "quarter" | "year" | "long_term") | null;
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
            /** Position */
            position?: number | null;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Status */
            status?: ("active" | "paused" | "completed" | "retired") | null;
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at?: string | null;
            /** Title */
            title?: string | null;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** GoalProgress */
        GoalProgress: {
            /** Changed Since Last Review */
            changed_since_last_review?: string | null;
            /** Completed Milestones */
            completed_milestones: number;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Goal Id */
            goal_id: string;
            /** Milestone Count */
            milestone_count: number;
            /** Progress Percent */
            progress_percent: number | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** GoalWork */
        GoalWork: {
            /** Actions */
            actions?: components["schemas"]["WorkAction"][];
            /**
             * Completed Count
             * @default 0
             */
            completed_count: number;
            /** Milestones */
            milestones?: components["schemas"]["WorkMilestone"][];
            /** Progress Percent */
            progress_percent?: number | null;
            /**
             * Total Count
             * @default 0
             */
            total_count: number;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HistoryItem */
        HistoryItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "plan_revision" | "review_snapshot";
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** State */
            state: {
                [key: string]: unknown;
            };
            /** Title */
            title: string;
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
        /** InterviewDebrief */
        InterviewDebrief: {
            /**
             * Candidate Notes
             * @default
             */
            candidate_notes: string;
            /** Created At */
            created_at: string;
            /** Employer Feedback */
            employer_feedback?: string | null;
            /**
             * Employer Feedback Source
             * @default user_reported_quote_not_independently_verified
             */
            employer_feedback_source: string;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Follow Up Items */
            follow_up_items?: string[];
            /**
             * Follow Up Status
             * @default draft_requires_approval
             */
            follow_up_status: string;
            /**
             * Interpretation
             * @default Öz değerlendirme; işverenin karar nedeni değildir.
             */
            interpretation: string;
            /** Interview Id */
            interview_id: string;
            /** New Story Proposals */
            new_story_proposals?: components["schemas"]["StoryProposal"][];
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Outcome If Known */
            outcome_if_known?: string | null;
            /** Perceived Gaps */
            perceived_gaps?: string[];
            /** Perceived Strengths */
            perceived_strengths?: string[];
            /** Questions Asked */
            questions_asked?: string[];
            /** Skill Signals */
            skill_signals: string[];
            /**
             * Source Type
             * @default user_report
             * @constant
             */
            source_type: "user_report";
            /**
             * Story Update Status
             * @default proposal_requires_approval
             */
            story_update_status: string;
            /** Story Updates */
            story_updates?: string[];
            /** Topics */
            topics?: string[];
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
        /** InterviewIntelligence */
        InterviewIntelligence: {
            debrief?: components["schemas"]["InterviewDebrief"] | null;
            /** Practice */
            practice?: components["schemas"]["InterviewPracticeSession"][];
            prep?: components["schemas"]["InterviewPrep"] | null;
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
        /** InterviewPracticeSession */
        InterviewPracticeSession: {
            /** Candidate Answer */
            candidate_answer: string;
            /**
             * Candidate Context Revision
             * @default
             */
            candidate_context_revision: string;
            /** Created At */
            created_at: string;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Feedback */
            feedback: {
                [key: string]: string;
            };
            /** Gaps */
            gaps: string[];
            /** Interview Id */
            interview_id: string;
            /**
             * Model
             * @default review-hints-v1
             */
            model: string;
            /**
             * Prep Input Revision
             * @default
             */
            prep_input_revision: string;
            /**
             * Provider
             * @default deterministic
             */
            provider: string;
            /** Question */
            question: string;
            /** Stage */
            stage: string | null;
            /** Strengths */
            strengths: string[];
        };
        /** InterviewPrep */
        InterviewPrep: {
            /** Behavioral Topics */
            behavioral_topics: string[];
            /** Candidate Context Revision */
            candidate_context_revision: string;
            /** Company Summary */
            company_summary: string;
            /** Created At */
            created_at: string;
            /** Evaluation Revision */
            evaluation_revision: string;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Focus Areas */
            focus_areas: string[];
            /** Input Revision */
            input_revision: string;
            /** Interview Id */
            interview_id: string;
            /** Interview Stage */
            interview_stage: string | null;
            /**
             * Is Stale
             * @default false
             */
            is_stale: boolean;
            /** Likely Questions */
            likely_questions: string[];
            /** Listing Fingerprint */
            listing_fingerprint: string;
            /**
             * Model
             * @default evidence-rules-v1
             */
            model: string;
            /** Opportunity Id */
            opportunity_id: string;
            /**
             * Provider
             * @default deterministic
             */
            provider: string;
            /** Questions To Ask */
            questions_to_ask: string[];
            /** Risks */
            risks: string[];
            /** Role Summary */
            role_summary: string;
            /** Story Recommendations */
            story_recommendations: components["schemas"]["StoryRecommendation"][];
            /** Technical Topics */
            technical_topics: string[];
            /** Unknowns */
            unknowns: string[];
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
        /** KeyResultIn */
        "KeyResultIn-Input": {
            /**
             * Baseline Value
             * @default 0
             */
            baseline_value: number | string;
            /** Description */
            description?: string | null;
            /**
             * Direction
             * @default increase
             * @enum {string}
             */
            direction: "increase" | "decrease";
            /** Manual Value */
            manual_value?: number | string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            source_config?: components["schemas"]["MetricConfig"];
            /**
             * Source Key
             * @default manual
             * @enum {string}
             */
            source_key: "manual" | "applications_applied" | "applications_interview" | "applications_offer" | "goal_milestones" | "linked_completion";
            /** Start At */
            start_at?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Target At */
            target_at?: string | null;
            /** Target Value */
            target_value: number | string;
            /** Title */
            title: string;
            /**
             * Trajectory Model
             * @default none
             * @enum {string}
             */
            trajectory_model: "linear" | "deadline" | "none";
            /**
             * Unit
             * @default adet
             */
            unit: string;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** KeyResultIn */
        "KeyResultIn-Output": {
            /**
             * Baseline Value
             * @default 0
             */
            baseline_value: string;
            /** Description */
            description?: string | null;
            /**
             * Direction
             * @default increase
             * @enum {string}
             */
            direction: "increase" | "decrease";
            /** Manual Value */
            manual_value?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            source_config?: components["schemas"]["MetricConfig"];
            /**
             * Source Key
             * @default manual
             * @enum {string}
             */
            source_key: "manual" | "applications_applied" | "applications_interview" | "applications_offer" | "goal_milestones" | "linked_completion";
            /** Start At */
            start_at?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Target At */
            target_at?: string | null;
            /** Target Value */
            target_value: string;
            /** Title */
            title: string;
            /**
             * Trajectory Model
             * @default none
             * @enum {string}
             */
            trajectory_model: "linear" | "deadline" | "none";
            /**
             * Unit
             * @default adet
             */
            unit: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** KeyResultOut */
        KeyResultOut: {
            /**
             * Baseline Value
             * @default 0
             */
            baseline_value: string;
            /** Description */
            description?: string | null;
            /**
             * Direction
             * @default increase
             * @enum {string}
             */
            direction: "increase" | "decrease";
            /**
             * Goal Id
             * Format: uuid
             */
            goal_id: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Manual Value */
            manual_value?: string | null;
            /** Measured At */
            measured_at: string | null;
            measurement: components["schemas"]["Measurement"];
            /**
             * Position
             * @default 0
             */
            position: number;
            source_config?: components["schemas"]["MetricConfig"];
            /**
             * Source Key
             * @default manual
             * @enum {string}
             */
            source_key: "manual" | "applications_applied" | "applications_interview" | "applications_offer" | "goal_milestones" | "linked_completion";
            /** Start At */
            start_at?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Target At */
            target_at?: string | null;
            /** Target Value */
            target_value: string;
            /** Title */
            title: string;
            /**
             * Trajectory Model
             * @default none
             * @enum {string}
             */
            trajectory_model: "linear" | "deadline" | "none";
            /**
             * Unit
             * @default adet
             */
            unit: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** KnockoutAnswerOut */
        KnockoutAnswerOut: {
            /**
             * Classification
             * @default needs_user_input
             * @enum {string}
             */
            classification: "safe_verified" | "needs_user_input" | "sensitive_user_decision";
            /**
             * Confidence
             * @default 1
             */
            confidence: number;
            /** Evidence */
            evidence: string;
            /** Evidence Refs */
            evidence_refs?: string[];
            /** Proposed Answer */
            proposed_answer: string;
            /** Question */
            question: string;
            /** Warning */
            warning?: string | null;
        };
        /** LearningContext */
        LearningContext: {
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "learning";
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
        /** LinkData */
        LinkData: {
            /**
             * Relation
             * @enum {string}
             */
            relation: "advances_goal" | "advances_goal_milestone" | "belongs_to" | "prepares_for" | "learns_from" | "references";
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
        /** Measurement */
        Measurement: {
            /**
             * Confidence
             * @default low
             * @enum {string}
             */
            confidence: "high" | "medium" | "low";
            /** Current Value */
            current_value: string | null;
            /** Evidence Refs */
            evidence_refs?: string[];
            /** Expected Percent */
            expected_percent?: number | null;
            /** Progress Percent */
            progress_percent: number | null;
            /** Reasons */
            reasons?: components["schemas"]["Reason"][];
            /**
             * Trajectory
             * @default unknown
             * @enum {string}
             */
            trajectory: "ahead" | "on_track" | "behind" | "not_applicable" | "unknown";
        };
        /** MetricConfig */
        MetricConfig: {
            /** Linked Entity Id */
            linked_entity_id?: string | null;
            /** Since */
            since?: string | null;
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
        /** NewArea */
        NewArea: {
            data: components["schemas"]["AreaData"];
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "learning.area";
        };
        /** NewGoal */
        "NewGoal-Input": {
            data: components["schemas"]["StudioGoalIn-Input"];
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /** Pillar Ref */
            pillar_ref?: string | null;
            /** Plan Ref */
            plan_ref?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "goal.create";
        };
        /** NewGoal */
        "NewGoal-Output": {
            data: components["schemas"]["StudioGoalIn-Output"];
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /** Pillar Ref */
            pillar_ref?: string | null;
            /** Plan Ref */
            plan_ref?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "goal.create";
        };
        /** NewMilestone */
        NewMilestone: {
            data: components["schemas"]["StudioMilestoneIn"];
            /** Goal Ref */
            goal_ref: string;
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "milestone.create";
        };
        /** NewNode */
        "NewNode-Input": {
            data: components["schemas"]["NodeData-Input"];
            /** Depends On */
            depends_on?: string[];
            /** Goal Ref */
            goal_ref: string;
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /** Target Ref */
            target_ref?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "roadmap.create";
        };
        /** NewNode */
        "NewNode-Output": {
            data: components["schemas"]["NodeData-Output"];
            /** Depends On */
            depends_on?: string[];
            /** Goal Ref */
            goal_ref: string;
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /** Target Ref */
            target_ref?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "roadmap.create";
        };
        /** NewPillar */
        "NewPillar-Input": {
            data: components["schemas"]["PillarIn-Input"];
            /** Key */
            key: string;
            /** Plan Ref */
            plan_ref: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "pillar.create";
        };
        /** NewPillar */
        "NewPillar-Output": {
            data: components["schemas"]["PillarIn-Output"];
            /** Key */
            key: string;
            /** Plan Ref */
            plan_ref: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "pillar.create";
        };
        /** NewPlan */
        NewPlan: {
            data: components["schemas"]["PlanIn"];
            /** Key */
            key: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "plan.create";
        };
        /** NewResource */
        NewResource: {
            data: components["schemas"]["ResourceData"];
            /** Key */
            key: string;
            /** Topic Ref */
            topic_ref: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "learning.resource";
        };
        /** NewTask */
        NewTask: {
            data: components["schemas"]["TaskData"];
            /** Key */
            key: string;
            /** Project Ref */
            project_ref?: string | null;
            /** Topic Ref */
            topic_ref?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "todo.create";
        };
        /** NewTopic */
        NewTopic: {
            /** Area Ref */
            area_ref: string;
            data: components["schemas"]["TopicData"];
            /** Key */
            key: string;
            /** Parent Ref */
            parent_ref?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "learning.topic";
        };
        /** NodeData */
        "NodeData-Input": {
            /**
             * Completion Gate
             * @default false
             */
            completion_gate: boolean;
            /** Description */
            description?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "period" | "phase" | "milestone" | "record" | "child_goal";
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Progress Bearing
             * @default true
             */
            progress_bearing: boolean;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** NodeData */
        "NodeData-Output": {
            /**
             * Completion Gate
             * @default false
             */
            completion_gate: boolean;
            /** Description */
            description?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "period" | "phase" | "milestone" | "record" | "child_goal";
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Progress Bearing
             * @default true
             */
            progress_bearing: boolean;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
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
        /** ObjectiveState */
        ObjectiveState: {
            /** Active Kr Count */
            active_kr_count: number;
            /**
             * Confidence
             * @enum {string}
             */
            confidence: "high" | "medium" | "low";
            /** Evidence Refs */
            evidence_refs: string[];
            /** Expected Percent */
            expected_percent: number | null;
            goal: components["schemas"]["GoalOut"];
            /** Key Results */
            key_results: components["schemas"]["KeyResultOut"][];
            /** Linked Entity Ids */
            linked_entity_ids: string[];
            /** Measurable Count */
            measurable_count: number;
            /** Milestone Progress Percent */
            milestone_progress_percent: number | null;
            /** Reasons */
            reasons: components["schemas"]["Reason"][];
            /**
             * Roadmap Completed Scope Count
             * @default 0
             */
            roadmap_completed_scope_count: number;
            /**
             * Roadmap Present
             * @default false
             */
            roadmap_present: boolean;
            /** Roadmap Progress Percent */
            roadmap_progress_percent?: number | null;
            /**
             * Roadmap Scope Count
             * @default 0
             */
            roadmap_scope_count: number;
            /** Strategic Progress Percent */
            strategic_progress_percent: number | null;
            /** Trajectory */
            trajectory: string;
            work?: components["schemas"]["GoalWork"];
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
        /** OnboardingState */
        OnboardingState: {
            /** Active Step */
            active_step?: string | null;
            /** Active Tour */
            active_tour?: string | null;
            /** Dismissed Hints */
            dismissed_hints?: string[];
            /**
             * Feed Setup
             * @default pending
             * @enum {string}
             */
            feed_setup: "pending" | "chosen" | "skipped";
            /** Journey */
            journey?: ("general" | "goal" | "planning" | "learning" | "career") | null;
            /**
             * Phase
             * @default welcome
             * @enum {string}
             */
            phase: "welcome" | "journey" | "sources" | "tour" | "checklist";
            /** Skipped Steps */
            skipped_steps?: string[];
            /**
             * Status
             * @default new
             * @enum {string}
             */
            status: "new" | "in_progress" | "completed" | "dismissed";
            /**
             * Version
             * @default 1
             * @constant
             */
            version: 1;
            /** Visited Steps */
            visited_steps?: string[];
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
            /** Client Uuid */
            client_uuid?: string | null;
            /** Compensation */
            compensation?: string | null;
            /** Country */
            country?: string | null;
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
            /** Published At */
            published_at?: string | null;
            /** Raw */
            raw?: {
                [key: string]: unknown;
            };
            /** Region */
            region?: string | null;
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
            /** Compensation */
            compensation?: string | null;
            /** Country */
            country?: string | null;
            /** Deadline At */
            deadline_at?: string | null;
            /** Follow Up At */
            follow_up_at?: string | null;
            /** Location */
            location?: string | null;
            /** Notes */
            notes?: string | null;
            /** Organization */
            organization?: string | null;
            /** Priority */
            priority?: number | null;
            /** Published At */
            published_at?: string | null;
            /** Raw */
            raw?: {
                [key: string]: unknown;
            } | null;
            /** Region */
            region?: string | null;
            /** Rejection Reason */
            rejection_reason?: string | null;
            /** Remote */
            remote?: string | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
        };
        /** PackageCoverLetterReviewIn */
        PackageCoverLetterReviewIn: {
            /**
             * Decision
             * @enum {string}
             */
            decision: "approved" | "rejected";
        };
        /** PackageCoverLetterReviewOut */
        PackageCoverLetterReviewOut: {
            /** Content Hash */
            content_hash?: string | null;
            /** Reviewed At */
            reviewed_at?: string | null;
            /**
             * Status
             * @default pending
             * @enum {string}
             */
            status: "pending" | "approved" | "rejected";
        };
        /** PillarIn */
        "PillarIn-Input": {
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** PillarIn */
        "PillarIn-Output": {
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** PillarOut */
        PillarOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Plan Id
             * Format: uuid
             */
            plan_id: string;
            /**
             * Position
             * @default 0
             */
            position: number;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** PlanIn */
        PlanIn: {
            /** Change Reason */
            change_reason?: string | null;
            /**
             * End At
             * Format: date-time
             */
            end_at: string;
            /** Narrative Path */
            narrative_path?: string | null;
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "archived" | "superseded";
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
        };
        /** PlanOut */
        PlanOut: {
            /** Change Reason */
            change_reason?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * End At
             * Format: date-time
             */
            end_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Narrative Path */
            narrative_path?: string | null;
            /** Revision */
            revision: number;
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "archived" | "superseded";
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
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
        /** PlanningConstraints */
        PlanningConstraints: {
            /** Available End Min */
            available_end_min?: number | null;
            /** Available Start Min */
            available_start_min?: number | null;
            /**
             * Capacity Confirmed
             * @default false
             */
            capacity_confirmed: boolean;
            /**
             * Daily Capacity Min
             * @default 30
             */
            daily_capacity_min: number;
            /** Unavailable Days */
            unavailable_days?: string[];
            /** Weekdays */
            weekdays?: number[];
        };
        /** PlanningContext */
        PlanningContext: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "planning";
            /** Todo Ids */
            todo_ids: string[];
        };
        /** PlanningIn */
        PlanningIn: {
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Todo Ids */
            todo_ids: string[];
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
             * @enum {string}
             */
            kind: "focus" | "short_break" | "long_break";
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
             * Source
             * @default timer
             * @enum {string}
             */
            source: "timer" | "manual";
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
             * @enum {string}
             */
            kind: "focus" | "short_break" | "long_break";
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
        /** PracticeIn */
        PracticeIn: {
            /** Candidate Answer */
            candidate_answer: string;
            /** Question */
            question: string;
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
            /**
             * Worker Active
             * @default false
             */
            worker_active: boolean;
            /** Worker Heartbeat */
            worker_heartbeat?: {
                [key: string]: unknown;
            } | null;
        };
        /** ProjectContext */
        ProjectContext: {
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "project";
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
        /** ProjectMilestoneProgress */
        ProjectMilestoneProgress: {
            /** Completed Milestones */
            completed_milestones: number;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Milestone Count */
            milestone_count: number;
            /** Progress Percent */
            progress_percent: number | null;
            /** Project Id */
            project_id: string;
            /** Title */
            title: string;
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
        /** ProjectResourceIn */
        ProjectResourceIn: {
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /** Title */
            title: string;
            /** Url */
            url: string;
        };
        /** ProjectResourceOut */
        ProjectResourceOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /** Url */
            url: string;
        };
        /** ProposalOut */
        ProposalOut: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Decided At */
            decided_at: string | null;
            /** Estimated Scope */
            estimated_scope: string | null;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Fingerprint */
            fingerprint: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Materialization Status
             * @enum {string}
             */
            materialization_status: "pending" | "materialized" | "unsupported_target" | "failed" | "stale";
            /** Rationale */
            rationale: string;
            /** Related Goal Id */
            related_goal_id: string | null;
            /** Sample Size */
            sample_size: number | null;
            /**
             * Status
             * @enum {string}
             */
            status: "proposed" | "approved" | "rejected" | "materialized" | "expired";
            /** Strategy Revision */
            strategy_revision: string;
            /** Target Id */
            target_id: string | null;
            /** Target Type */
            target_type: string | null;
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "goal" | "milestone" | "learning" | "project" | "todo";
            /** Warnings */
            warnings?: string[];
        };
        /** ProviderMetadata */
        ProviderMetadata: {
            /** Description */
            description: string;
            /**
             * Key
             * @enum {string}
             */
            key: "manual" | "applications_applied" | "applications_interview" | "applications_offer" | "goal_milestones" | "linked_completion";
            /** Label */
            label: string;
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
        /** Reason */
        Reason: {
            /** Code */
            code: string;
            /** Explanation */
            explanation: string;
        };
        /** RecommendedAction */
        RecommendedAction: {
            /** Evidence Refs */
            evidence_refs: string[];
            /** Title */
            title: string;
            /** Why */
            why: string;
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
        /** ResourceData */
        ResourceData: {
            /**
             * Kind
             * @default exercise
             * @enum {string}
             */
            kind: "link" | "video" | "article" | "course" | "book" | "doc" | "exercise";
            /** Note */
            note?: string | null;
            /** Title */
            title: string;
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
        /** ReviewContext */
        ReviewContext: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "review";
            /**
             * Period Kind
             * @enum {string}
             */
            period_kind: "daily" | "weekly" | "monthly" | "yearly";
            /**
             * Period Start
             * Format: date
             */
            period_start: string;
            /** Review Id */
            review_id?: string | null;
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
            /** Career Goals */
            career_goals?: components["schemas"]["CareerGoalReviewProgress"][];
            /** Career Proposals Pending */
            career_proposals_pending?: number;
            flashcards: components["schemas"]["FlashcardReviewStats"];
            focus: components["schemas"]["FocusReviewStats"];
            github: components["schemas"]["GithubReviewStats"];
            /** Habits */
            habits: {
                [key: string]: number;
            };
            /** Strategy Snapshot */
            strategy_snapshot?: {
                [key: string]: unknown;
            } | null;
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
        /** RoadmapNodeOut */
        RoadmapNodeOut: {
            /** Canonical Percent */
            canonical_percent?: number | null;
            /**
             * Completed
             * @default false
             */
            completed: boolean;
            /**
             * Completion Gate
             * @default false
             */
            completion_gate: boolean;
            /** Dependencies */
            dependencies?: string[];
            /** Description */
            description?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /**
             * Missing
             * @default false
             */
            missing: boolean;
            /** Parent Id */
            parent_id?: string | null;
            /** Percent */
            percent?: number | null;
            /**
             * Persisted
             * @default true
             */
            persisted: boolean;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Progress Bearing
             * @default true
             */
            progress_bearing: boolean;
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
            /** Target Type */
            target_type?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Weight
             * @default 1
             */
            weight: number;
        };
        /** RoadmapOut */
        RoadmapOut: {
            /**
             * Completed Requirements
             * @default 0
             */
            completed_requirements: number;
            /**
             * Completed Scope Count
             * @default 0
             */
            completed_scope_count: number;
            /**
             * Goal Id
             * Format: uuid
             */
            goal_id: string;
            /**
             * Known Requirements
             * @default 0
             */
            known_requirements: number;
            /**
             * Legacy
             * @default false
             */
            legacy: boolean;
            /** Nodes */
            nodes: components["schemas"]["RoadmapNodeOut"][];
            /** Percent */
            percent?: number | null;
            /**
             * Scope Count
             * @default 0
             */
            scope_count: number;
            /**
             * Total Requirements
             * @default 0
             */
            total_requirements: number;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
            /**
             * Unplanned Count
             * @default 0
             */
            unplanned_count: number;
            /** Warnings */
            warnings?: string[];
        };
        /** RoadmapOwner */
        RoadmapOwner: {
            /**
             * Goal Id
             * Format: uuid
             */
            goal_id: string;
            /**
             * Node Id
             * Format: uuid
             */
            node_id: string;
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
        /** SaveKR */
        "SaveKR-Input": {
            data: components["schemas"]["KeyResultIn-Input"];
            /** Goal Ref */
            goal_ref: string;
            /** Key */
            key: string;
            /** Target Id */
            target_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "key_result.save";
        };
        /** SaveKR */
        "SaveKR-Output": {
            data: components["schemas"]["KeyResultIn-Output"];
            /** Goal Ref */
            goal_ref: string;
            /** Key */
            key: string;
            /** Target Id */
            target_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "key_result.save";
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
        /** ScheduleData */
        ScheduleData: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /**
             * Duration Min
             * @default 30
             */
            duration_min: number;
            /** Note */
            note?: string | null;
            /** Start Min */
            start_min?: number | null;
        };
        /** ScheduleTask */
        ScheduleTask: {
            data: components["schemas"]["ScheduleData"];
            /** Key */
            key: string;
            /** Replace Slot Id */
            replace_slot_id?: string | null;
            /** Task Ref */
            task_ref: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "plan.schedule";
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
        /** SharedDeckOut */
        SharedDeckOut: {
            /** Has Media */
            has_media: boolean;
            /** Id */
            id: number;
            /** Likes */
            likes: number;
            /** Notes */
            notes: number;
            /** Title */
            title: string;
            /** Url */
            url: string;
        };
        /** SharedDeckPreview */
        SharedDeckPreview: {
            /** Has Media */
            has_media: boolean;
            /** Id */
            id: number;
            /** Notes */
            notes: number;
            /** Samples */
            samples: string[][];
            /** Size Bytes */
            size_bytes: number;
            /** Title */
            title: string;
            /** Url */
            url: string;
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
        /** SkillGapSignal */
        SkillGapSignal: {
            /** Confidence */
            confidence: string;
            /** Evidence Refs */
            evidence_refs: string[];
            /**
             * Explicit Feedback Mentions
             * @default 0
             */
            explicit_feedback_mentions: number;
            /** Interview Mentions */
            interview_mentions: number;
            /** Missing Count */
            missing_count: number;
            /** Opportunities Seen */
            opportunities_seen: number;
            /** Partial Count */
            partial_count: number;
            /** Requirement */
            requirement: string;
            /** Role Families */
            role_families: string[];
            /** Strong Count */
            strong_count: number;
            /**
             * Trend
             * @default unavailable_no_historical_snapshots
             */
            trend: string;
            /** Unknown Count */
            unknown_count: number;
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
        /** SnapshotMeasurement */
        SnapshotMeasurement: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Measured At */
            measured_at: string | null;
            measurement: components["schemas"]["Measurement"];
            /** Source Key */
            source_key: string;
            /** Target Value */
            target_value: string;
            /** Title */
            title: string;
            /** Unit */
            unit: string;
        };
        /** SnapshotNode */
        SnapshotNode: {
            /** Canonical Percent */
            canonical_percent?: number | null;
            /**
             * Completed
             * @default false
             */
            completed: boolean;
            /**
             * Completion Gate
             * @default false
             */
            completion_gate: boolean;
            /** Dependencies */
            dependencies?: string[];
            /** Description */
            description?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Index */
            index: number;
            /** Kind */
            kind: string;
            /**
             * Missing
             * @default false
             */
            missing: boolean;
            /** Parent Id */
            parent_id?: string | null;
            /** Percent */
            percent?: number | null;
            /**
             * Persisted
             * @default true
             */
            persisted: boolean;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Progress Bearing
             * @default true
             */
            progress_bearing: boolean;
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
            /** Target Type */
            target_type?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Weight
             * @default 1
             */
            weight: number;
        };
        /** SnapshotOutcome */
        SnapshotOutcome: {
            /** Measurements */
            measurements: components["schemas"]["SnapshotMeasurement"][];
            /** Percent */
            percent: string | null;
        };
        /** SnapshotProject */
        SnapshotProject: {
            /** Completed */
            completed: number;
            /** Coverage */
            coverage: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Percent */
            percent: number | null;
            /** Title */
            title: string;
            /** Total */
            total: number;
        };
        /** SnapshotResource */
        SnapshotResource: {
            /** Has Url */
            has_url: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Missing Source
             * @default false
             */
            missing_source: boolean;
            /**
             * Pending Need
             * @default false
             */
            pending_need: boolean;
            /** Source */
            source: string;
            /** Title */
            title: string;
            /**
             * Topic Id
             * Format: uuid
             */
            topic_id: string;
        };
        /** SnapshotReview */
        SnapshotReview: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Execution Percent */
            execution_percent?: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Outcome Percent */
            outcome_percent?: number | null;
        };
        /** SnapshotRoadmap */
        SnapshotRoadmap: {
            /** Known */
            known: number;
            /** Nodes */
            nodes: components["schemas"]["SnapshotNode"][];
            /** Percent */
            percent: number | null;
            /** Requirements */
            requirements: number;
            /** Truncated */
            truncated: boolean;
        };
        /** SnapshotSlot */
        SnapshotSlot: {
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
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Start Min */
            start_min: number | null;
        };
        /** SnapshotTask */
        SnapshotTask: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Recurring Template */
            recurring_template: boolean;
            /** Status */
            status: string;
            /** Title */
            title: string;
        };
        /** SnapshotTopic */
        SnapshotTopic: {
            /**
             * Area Id
             * Format: uuid
             */
            area_id: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Status */
            status: string;
            /** Title */
            title: string;
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
         * SourceRef
         * @description İncelenebilir kaynak referansı (§88/§89).
         *
         *     Deterministik ve tekrarlanabilirdir; mutlak dosya yolu taşımaz.
         */
        SourceRef: {
            /**
             * Domain
             * @enum {string}
             */
            domain: "operational" | "review" | "vault" | "evidence" | "aggregate";
            /** Entity Id */
            entity_id?: string | null;
            /** Evidence Id */
            evidence_id?: string | null;
            /**
             * Excerpt
             * @description Sınırlı kaynak alıntısı.
             */
            excerpt?: string | null;
            /**
             * Kind
             * @description Kaynak türü, ör. 'event', 'review', 'daily_note', 'aggregate'.
             */
            kind: string;
            /**
             * Locator
             * @description Dosya içi konum (göreli yol + satır aralığı).
             */
            locator?: string | null;
            /**
             * Ref
             * @description Deterministik referans, ör. 'event:12345' veya 'vault:10 Daily/….md:L12-L18'.
             */
            ref: string;
            /** Timestamp */
            timestamp?: string | null;
            /** Title */
            title?: string | null;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
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
            /**
             * Items Seen
             * @default 0
             */
            items_seen: number;
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
            /** Telemetry */
            telemetry?: {
                [key: string]: unknown;
            } | null;
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
        /** StoryProposal */
        StoryProposal: {
            /** Action */
            action: string;
            /** Result */
            result: string;
            /** Situation */
            situation: string;
            /** Task */
            task: string;
        };
        /** StoryRecommendation */
        StoryRecommendation: {
            /**
             * Adaptation Notes
             * @default Yalnızca doğrulayabildiğin ayrıntıları kullan.
             */
            adaptation_notes: string;
            /** Evidence Refs */
            evidence_refs: string[];
            /** Likely Question Types */
            likely_question_types: string[];
            /** Story Id */
            story_id: string;
            /** Why Relevant */
            why_relevant: string;
        };
        /** StrategicSignal */
        StrategicSignal: {
            /** Caveat */
            caveat: string;
            /**
             * Confidence
             * @enum {string}
             */
            confidence: "low" | "medium" | "high";
            /** Evidence Refs */
            evidence_refs?: string[];
            /**
             * Evidence Type
             * @enum {string}
             */
            evidence_type: "observed_fact" | "explicit_feedback" | "descriptive_pattern" | "model_interpretation" | "user_statement" | "approved_memory";
            /** Sample Size */
            sample_size: number;
            /** Title */
            title: string;
            /** Topic */
            topic?: string | null;
        };
        /** StrategyHistory */
        StrategyHistory: {
            /** Alignment Delta */
            alignment_delta?: number | null;
            /** Comparable */
            comparable: boolean;
            /** Comparison Reason */
            comparison_reason: string;
            /** Items */
            items: components["schemas"]["HistoryItem"][];
            /** Progress Deltas */
            progress_deltas?: {
                [key: string]: number;
            };
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
        };
        /** StrategyOverview */
        StrategyOverview: {
            alignment: components["schemas"]["Alignment"];
            /**
             * Calculated At
             * Format: date-time
             */
            calculated_at: string;
            /** Findings */
            findings: components["schemas"]["Finding"][];
            /**
             * Method
             * @default strategy-v1
             */
            method: string;
            /** Objectives */
            objectives: components["schemas"]["ObjectiveState"][];
            /** Pillar Progress */
            pillar_progress: components["schemas"]["Aggregate"][];
            /** Pillars */
            pillars: components["schemas"]["PillarOut"][];
            /** Plan Progress */
            plan_progress: components["schemas"]["Aggregate"][];
            /** Plans */
            plans: components["schemas"]["PlanOut"][];
            /** Providers */
            providers: components["schemas"]["ProviderMetadata"][];
            /**
             * Schema Version
             * @default 1
             */
            schema_version: number;
            /** Warnings */
            warnings: components["schemas"]["Reason"][];
        };
        /**
         * StrategyWindow
         * @enum {integer}
         */
        StrategyWindow: 7 | 30 | 90;
        /** StreakOut */
        StreakOut: {
            /** Current */
            current: number;
            /** Longest */
            longest: number;
        };
        /** StudioApplied */
        StudioApplied: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Plan Slot Id */
            plan_slot_id?: string | null;
            /** Type */
            type: string;
        };
        /** StudioConsentIn */
        StudioConsentIn: {
            /** Allowed */
            allowed: boolean;
            /** Policy Id */
            policy_id?: string | null;
            /** Revision */
            revision: string;
        };
        /** StudioConsentOut */
        StudioConsentOut: {
            /**
             * Allowed
             * @default false
             */
            allowed: boolean;
            /** Policy Id */
            policy_id?: string | null;
            /** Revision */
            revision: string;
        };
        /** StudioDecisionIn */
        StudioDecisionIn: {
            /**
             * Decision
             * @enum {string}
             */
            decision: "approve" | "reject";
            /** Fingerprint */
            fingerprint: string;
            /**
             * Revision Id
             * Format: uuid
             */
            revision_id: string;
        };
        /** StudioGoalIn */
        "StudioGoalIn-Input": {
            /** Description */
            description?: string | null;
            /**
             * Horizon
             * @default quarter
             * @enum {string}
             */
            horizon: "short_term" | "quarter" | "year" | "long_term";
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
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
            /** Source Memory Id */
            source_memory_id?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at?: string | null;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** StudioGoalIn */
        "StudioGoalIn-Output": {
            /** Description */
            description?: string | null;
            /**
             * Horizon
             * @default quarter
             * @enum {string}
             */
            horizon: "short_term" | "quarter" | "year" | "long_term";
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
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
            /** Source Memory Id */
            source_memory_id?: string | null;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "paused" | "completed" | "retired";
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at?: string | null;
            /** Title */
            title: string;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** StudioGoalPatch */
        "StudioGoalPatch-Input": {
            /** Description */
            description?: string | null;
            /** Horizon */
            horizon?: ("short_term" | "quarter" | "year" | "long_term") | null;
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
            /** Position */
            position?: number | null;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Status */
            status?: ("active" | "paused" | "completed" | "retired") | null;
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at?: string | null;
            /** Title */
            title?: string | null;
            /**
             * Weight
             * @default 1
             */
            weight: number | string;
        };
        /** StudioGoalPatch */
        "StudioGoalPatch-Output": {
            /** Description */
            description?: string | null;
            /** Horizon */
            horizon?: ("short_term" | "quarter" | "year" | "long_term") | null;
            /** Parent Goal Id */
            parent_goal_id?: string | null;
            /** Pillar Id */
            pillar_id?: string | null;
            /** Position */
            position?: number | null;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Status */
            status?: ("active" | "paused" | "completed" | "retired") | null;
            /** Strategic Plan Id */
            strategic_plan_id?: string | null;
            /** Target At */
            target_at?: string | null;
            /** Title */
            title?: string | null;
            /**
             * Weight
             * @default 1
             */
            weight: string;
        };
        /** StudioMilestoneIn */
        StudioMilestoneIn: {
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
        /** StudioMilestonePatch */
        StudioMilestonePatch: {
            /** Completed */
            completed?: boolean | null;
            /** Due At */
            due_at?: string | null;
            /** Position */
            position?: number | null;
            /** Title */
            title?: string | null;
        };
        /** StudioProposal */
        "StudioProposal-Input": {
            /** Assumptions */
            assumptions?: string[];
            /** Evidence Refs */
            evidence_refs?: string[];
            /** Missing Information */
            missing_information?: string[];
            /** Operations */
            operations: (components["schemas"]["NewPlan"] | components["schemas"]["NewPillar-Input"] | components["schemas"]["NewGoal-Input"] | components["schemas"]["EditGoal-Input"] | components["schemas"]["SaveKR-Input"] | components["schemas"]["NewMilestone"] | components["schemas"]["EditMilestone"] | components["schemas"]["NewNode-Input"] | components["schemas"]["EditNode-Input"] | components["schemas"]["NewArea"] | components["schemas"]["NewTopic"] | components["schemas"]["NewTask"] | components["schemas"]["ScheduleTask"] | components["schemas"]["ConnectRecord"] | components["schemas"]["NewResource"] | components["schemas"]["EditTask"])[];
            planning?: components["schemas"]["PlanningConstraints"] | null;
            /** Rationale */
            rationale: string;
            /**
             * Schema Version
             * @default 1
             * @enum {integer}
             */
            schema_version: 1 | 2;
            /** Warnings */
            warnings?: string[];
        };
        /** StudioProposal */
        "StudioProposal-Output": {
            /** Assumptions */
            assumptions?: string[];
            /** Evidence Refs */
            evidence_refs?: string[];
            /** Missing Information */
            missing_information?: string[];
            /** Operations */
            operations: (components["schemas"]["NewPlan"] | components["schemas"]["NewPillar-Output"] | components["schemas"]["NewGoal-Output"] | components["schemas"]["EditGoal-Output"] | components["schemas"]["SaveKR-Output"] | components["schemas"]["NewMilestone"] | components["schemas"]["EditMilestone"] | components["schemas"]["NewNode-Output"] | components["schemas"]["EditNode-Output"] | components["schemas"]["NewArea"] | components["schemas"]["NewTopic"] | components["schemas"]["NewTask"] | components["schemas"]["ScheduleTask"] | components["schemas"]["ConnectRecord"] | components["schemas"]["NewResource"] | components["schemas"]["EditTask"])[];
            planning?: components["schemas"]["PlanningConstraints"] | null;
            /** Rationale */
            rationale: string;
            /**
             * Schema Version
             * @default 1
             * @enum {integer}
             */
            schema_version: 1 | 2;
            /** Warnings */
            warnings?: string[];
        };
        /** StudioRevisionOut */
        StudioRevisionOut: {
            /** Before */
            before: {
                [key: string]: unknown;
            };
            /** Error */
            error?: string | null;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Fingerprint */
            fingerprint: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            proposal: components["schemas"]["StudioProposal-Output"];
            /** Results */
            results: {
                [key: string]: components["schemas"]["StudioApplied"];
            };
            /** State */
            state: string;
        };
        /** StudioRuntime */
        StudioRuntime: {
            /** Model */
            model: string;
            /**
             * Provider
             * @enum {string}
             */
            provider: "custom" | "openai-codex" | "nous";
        };
        /** StudioSessionIn */
        StudioSessionIn: {
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /** Context */
            context?: (components["schemas"]["ReviewContext"] | components["schemas"]["ProjectContext"] | components["schemas"]["GoalContext"] | components["schemas"]["CareerContext"] | components["schemas"]["LearningContext"] | components["schemas"]["PlanningContext"]) | null;
            /** Goal Id */
            goal_id?: string | null;
            /**
             * Long Term
             * @default false
             */
            long_term: boolean;
            /**
             * Mode
             * @default draft
             * @enum {string}
             */
            mode: "draft" | "feedback" | "living";
        };
        /** StudioSessionOut */
        StudioSessionOut: {
            /** Context */
            context?: (components["schemas"]["ReviewContext"] | components["schemas"]["ProjectContext"] | components["schemas"]["GoalContext"] | components["schemas"]["CareerContext"] | components["schemas"]["LearningContext"] | components["schemas"]["PlanningContext"]) | null;
            /** Error */
            error?: string | null;
            /** Goal Id */
            goal_id?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Messages */
            messages: {
                [key: string]: unknown;
            }[];
            /**
             * Mode
             * @default draft
             * @enum {string}
             */
            mode: "draft" | "feedback" | "living";
            pending_turn?: components["schemas"]["StudioTurnIn"] | null;
            /**
             * Progress
             * @default
             */
            progress: string;
            revision: components["schemas"]["StudioRevisionOut"] | null;
            runtime?: components["schemas"]["StudioRuntime"] | null;
            /** State */
            state: string;
        };
        /** StudioStatus */
        StudioStatus: {
            /** Configured Model */
            configured_model?: string | null;
            consent?: components["schemas"]["StudioConsentOut"] | null;
            /** Hermes Version */
            hermes_version?: string | null;
            /** Local */
            local?: boolean | null;
            /** Message */
            message: string;
            /**
             * Profile
             * @default forkos-goal-studio
             */
            profile: string;
            /** Provider */
            provider?: ("local_custom" | "codex_oauth" | "nous_portal") | null;
            /** Provider Label */
            provider_label?: string | null;
            /**
             * Provider Notice
             * @default Yalnız seçili bağlamın sınırlı özeti ve gönderdiğin mesaj kullanılır; sohbet kayıt değişikliği onayı değildir.
             */
            provider_notice: string;
            /**
             * State
             * @enum {string}
             */
            state: "not_configured" | "unavailable" | "unsupported" | "consent_required" | "ready";
            /**
             * Tools Verified
             * @default false
             */
            tools_verified: boolean;
            /**
             * Topology
             * @default native
             * @enum {string}
             */
            topology: "native" | "host_bridge";
        };
        /** StudioTurnIn */
        StudioTurnIn: {
            /**
             * Client Uuid
             * Format: uuid
             */
            client_uuid: string;
            /** Message */
            message: string;
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
        /** TagOut */
        TagOut: {
            /** Count */
            count: number;
            /** Name */
            name: string;
        };
        /** TaskData */
        TaskData: {
            /** Description */
            description?: string | null;
            /** Due At */
            due_at?: string | null;
            /**
             * Priority
             * @default 2
             */
            priority: number;
            /** Title */
            title: string;
        };
        /** TaskPatch */
        TaskPatch: {
            /** Description */
            description?: string | null;
            /** Due At */
            due_at?: string | null;
            /** Priority */
            priority?: number | null;
            /** Title */
            title?: string | null;
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
            /** Client Uuid */
            client_uuid?: string | null;
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
        /** TopicData */
        TopicData: {
            /** Description */
            description?: string | null;
            /** Title */
            title: string;
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
        /** WorkAction */
        WorkAction: {
            /** Completed */
            completed: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Milestone Ids */
            milestone_ids?: string[];
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "todo" | "study_topic";
        };
        /** WorkMilestone */
        WorkMilestone: {
            /** Action Ids */
            action_ids?: string[];
            /** Completed */
            completed: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Manual Completed */
            manual_completed: boolean;
            /** Progress Percent */
            progress_percent: number;
            /** Title */
            title: string;
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
    career_insights_api_career_insights_get: {
        parameters: {
            query?: {
                days?: number;
                minimum?: number;
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
                    "application/json": components["schemas"]["CareerAnalyticsSnapshot"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
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
    debrief_interview_intelligence_api_career_interviews__id__debrief_post: {
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
                "application/json": components["schemas"]["DebriefIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InterviewDebrief"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_interview_intelligence_api_career_interviews__id__intelligence_get: {
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
                    "application/json": components["schemas"]["InterviewIntelligence"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    practice_interview_intelligence_api_career_interviews__id__practice_post: {
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
                "application/json": components["schemas"]["PracticeIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InterviewPracticeSession"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    prepare_interview_intelligence_api_career_interviews__id__prepare_post: {
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
                    "application/json": components["schemas"]["InterviewPrep"];
                };
            };
            /** @description Validation Error */
            422: {
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
    career_strategy_api_career_strategy_get: {
        parameters: {
            query?: {
                days?: number;
                minimum?: number;
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
                    "application/json": components["schemas"]["CareerStrategySnapshot"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    career_strategy_proposals_api_career_strategy_proposals_get: {
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
                    "application/json": components["schemas"]["ProposalOut"][];
                };
            };
        };
    };
    refresh_career_strategy_proposals_api_career_strategy_proposals_refresh_post: {
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
                    "application/json": components["schemas"]["ProposalOut"][];
                };
            };
        };
    };
    approve_career_strategy_proposal_api_career_strategy_proposals__proposal_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ProposalOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_career_strategy_proposal_api_career_strategy_proposals__proposal_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ProposalOut"];
                };
            };
            /** @description Validation Error */
            422: {
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
    prepare_schedule_api_execution_planning_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanningIn"];
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
    shared_decks_api_flashcard_catalog_get: {
        parameters: {
            query?: {
                search?: string;
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
                    "application/json": components["schemas"]["SharedDeckOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_shared_deck_api_flashcard_catalog__shared_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                shared_id: number;
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
                    "application/json": components["schemas"]["SharedDeckPreview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_shared_deck_api_flashcard_catalog__shared_id__import_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                shared_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
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
    update_milestone_api_goal_milestones__milestone_id__patch: {
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
                "application/json": components["schemas"]["GoalMilestonePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoalMilestoneOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    goals_api_goals_get: {
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
                    "application/json": components["schemas"]["GoalOut"][];
                };
            };
        };
    };
    create_goal_api_goals_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoalIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoalOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    roadmap_owner_api_goals_roadmap_nodes__node_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                node_id: string;
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
                    "application/json": components["schemas"]["RoadmapOwner"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    strategy_history_api_goals_strategy_history_get: {
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
                    "application/json": components["schemas"]["StrategyHistory"];
                };
            };
        };
    };
    strategy_overview_api_goals_strategy_overview_get: {
        parameters: {
            query?: {
                days?: components["schemas"]["StrategyWindow"];
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
                    "application/json": components["schemas"]["StrategyOverview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    plan_create_api_goals_strategy_plans_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    plan_update_api_goals_strategy_plans__plan_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pillar_create_api_goals_strategy_plans__plan_id__pillars_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PillarIn-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PillarOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pillar_update_api_goals_strategy_plans__plan_id__pillars__pillar_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
                pillar_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PillarIn-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PillarOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    consent_api_goals_studio_consent_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StudioConsentIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudioConsentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    context_api_goals_studio_context_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewContext"] | components["schemas"]["ProjectContext"] | components["schemas"]["GoalContext"] | components["schemas"]["CareerContext"] | components["schemas"]["LearningContext"] | components["schemas"]["PlanningContext"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssistanceSummary"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_api_goals_studio_sessions_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StudioSessionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_api_goals_studio_sessions__session_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    decide_api_goals_studio_sessions__session_id__decision_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StudioDecisionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    events_api_goals_studio_sessions__session_id__events_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
    revise_api_goals_studio_sessions__session_id__proposal_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StudioProposal-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stop_api_goals_studio_sessions__session_id__stop_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    turn_api_goals_studio_sessions__session_id__turns_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StudioTurnIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    status_api_goals_studio_status_get: {
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
                    "application/json": components["schemas"]["StudioStatus"];
                };
            };
        };
    };
    goal_api_goals__goal_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
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
                    "application/json": components["schemas"]["GoalOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_goal_api_goals__goal_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoalPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoalOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_goal_action_api_goals__goal_id__actions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoalActionIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoalActionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    living_conversation_api_goals__goal_id__conversation_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
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
                    "application/json": components["schemas"]["StudioSessionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    kr_create_api_goals__goal_id__key_results_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KeyResultIn-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KeyResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    kr_update_api_goals__goal_id__key_results__kr_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
                kr_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KeyResultIn-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["KeyResultOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_milestone_api_goals__goal_id__milestones_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoalMilestoneIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GoalMilestoneOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    roadmap_read_api_goals__goal_id__roadmap_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
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
                    "application/json": components["schemas"]["RoadmapOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    living_workspace_api_goals__goal_id__workspace_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                goal_id: string;
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
                    "application/json": components["schemas"]["GoalContextSnapshot"];
                };
            };
            /** @description Validation Error */
            422: {
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
    huggingface_papers_api_news_huggingface_papers_get: {
        parameters: {
            query?: {
                date?: string | null;
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
    review_application_package_cover_letter_api_opportunities__id__application_package_review_cover_letter_post: {
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
                "application/json": components["schemas"]["PackageCoverLetterReviewIn"];
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
    update_api_pomodoro__pomo_id__put: {
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
                "application/json": components["schemas"]["PomodoroManual"];
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
    project_resources_api_projects__project_id__resources_get: {
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
                    "application/json": components["schemas"]["ProjectResourceOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_project_resource_api_projects__project_id__resources_post: {
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
                "application/json": components["schemas"]["ProjectResourceIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectResourceOut"];
                };
            };
            /** @description Validation Error */
            422: {
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
    career_ops_providers_api_sources_career_ops_providers_get: {
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
    forkjob_core_config_api_sources_forkjob_core_config_get: {
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
    forkjob_core_config_update_api_sources_forkjob_core_config_put: {
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
    forkjob_core_env_api_sources_forkjob_core_env_get: {
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
                    "application/json": components["schemas"]["ForkjobCoreEnvOut"];
                };
            };
        };
    };
    forkjob_core_linkedin_profiles_api_sources_forkjob_core_linkedin_profiles_get: {
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
    forkjob_core_linkedin_profiles_save_api_sources_forkjob_core_linkedin_profiles_put: {
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
                scope?: "opportunity";
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
                scope?: "opportunity";
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
    get_experience_api_system_experience_get: {
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
                    "application/json": components["schemas"]["ExperienceOut"];
                };
            };
        };
    };
    put_experience_api_system_experience_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExperienceUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExperienceOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    repair_experience_api_system_experience_repair_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExperienceRepairIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExperienceOut"];
                };
            };
            /** @description Validation Error */
            422: {
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
