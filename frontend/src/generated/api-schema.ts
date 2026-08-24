export interface paths {
    "/api/activity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Activity */
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
        delete?: never;
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
         * @description JSON yedegini geri yukler.
         *
         *     Idempotent + cakismasiz: var olan kayitlara dokunulmaz, eksikler eklenir.
         *     Ayni yedek defalarca yuklenebilir. (Opsiyonel: Yerel dosyayla cagirilir.)
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
    "/api/bookmarks/collections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Collections */
        get: operations["collections_api_bookmarks_collections_get"];
        put?: never;
        post?: never;
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
    "/api/books": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Books */
        get: operations["books_api_books_get"];
        put?: never;
        /** Add Book */
        post: operations["add_book_api_books_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/books/{id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Book */
        delete: operations["delete_book_api_books__id__delete"];
        options?: never;
        head?: never;
        /** Patch Book */
        patch: operations["patch_book_api_books__id__patch"];
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
    "/api/courses/{id}": {
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
        delete: operations["delete_course_api_courses__id__delete"];
        options?: never;
        head?: never;
        /** Patch Course */
        patch: operations["patch_course_api_courses__id__patch"];
        trace?: never;
    };
    "/api/deadlines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Deadlines */
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
    "/api/entities/{entity_id}/related": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Related */
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
    "/api/expenses/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Summary */
        get: operations["summary_api_expenses_summary_get"];
        put?: never;
        post?: never;
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
    "/api/github/activity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Github Activity */
        get: operations["github_activity_api_github_activity_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/github/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sync Github */
        post: operations["sync_github_api_github_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/habits": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Habits */
        get: operations["list_habits_api_habits_get"];
        put?: never;
        /** Create Habit */
        post: operations["create_habit_api_habits_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/habits/grid": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Habit Grid */
        get: operations["habit_grid_api_habits_grid_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/habits/{habit_id}": {
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
         * Delete Habit
         * @description Aliskanligi ve gunlugunu siler.
         *
         *     Birakmak icin `active=false` yeter (gecmis kalir); bu uc kaydi tamamen
         *     kaldirir -- yanlis eklenmis bir aliskanlik icin.
         */
        delete: operations["delete_habit_api_habits__habit_id__delete"];
        options?: never;
        head?: never;
        /** Update Habit */
        patch: operations["update_habit_api_habits__habit_id__patch"];
        trace?: never;
    };
    "/api/habits/{habit_id}/check": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Check Habit */
        post: operations["check_habit_api_habits__habit_id__check_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/learning/queue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Queue */
        get: operations["queue_api_learning_queue_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
        get?: never;
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
        /** Media Dashboard */
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
    "/api/media/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search Metadata */
        get: operations["search_metadata_api_media_search_get"];
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
    "/api/projects/{project_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Project Timeline
         * @description Projede ne olduysa -- kendi olaylari, gorev olaylari, commit'ler.
         */
        get: operations["project_timeline_api_projects__project_id__timeline_get"];
        put?: never;
        post?: never;
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
    "/api/sources/catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Source Catalog */
        get: operations["source_catalog_api_sources_catalog_get"];
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
         *     source_ids verilirse yalnizca onlar; kind verilirse o turun tamami; ikisi
         *     de bossa katalogun hepsi. API yalnızca kalıcı batch oluşturur; çekimi
         *     worker yapar ve ilerleme /sources/sync'ten izlenir.
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
    "/api/study/topics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topics */
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
        get?: never;
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
    "/api/study/topics/{topic_id}/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stats */
        get: operations["stats_api_study_topics__topic_id__stats_get"];
        put?: never;
        post?: never;
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
        /** List Views */
        get: operations["list_views_api_views_get"];
        put?: never;
        /** Create View */
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
            kind: "calendar" | "todo" | "rss" | "media";
            /** Media Kind */
            media_kind?: string | null;
            /** Media Status */
            media_status?: string | null;
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
            /** Media */
            media?: components["schemas"]["AgendaRow"][];
            /** Rss */
            rss?: components["schemas"]["AgendaRow"][];
            /** Todos */
            todos?: components["schemas"]["AgendaRow"][];
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
        /** Body_import_opml_api_rss_import_post */
        Body_import_opml_api_rss_import_post: {
            /** File */
            file: string;
        };
        /** Body_restore_backup_api_backup_restore_post */
        Body_restore_backup_api_backup_restore_post: {
            /** File */
            file: string;
        };
        /** BookIn */
        BookIn: {
            /** Author */
            author?: string | null;
            /**
             * Current Page
             * @default 0
             */
            current_page: number;
            /** Notes */
            notes?: string | null;
            /** Rating */
            rating?: number | null;
            /**
             * Status
             * @default want
             */
            status: string;
            /** Title */
            title: string;
            /** Total Pages */
            total_pages?: number | null;
        };
        /** BookPatch */
        BookPatch: {
            /** Current Page */
            current_page?: number | null;
            /** Notes */
            notes?: string | null;
            /** Rating */
            rating?: number | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
        };
        /** BookmarkOut */
        BookmarkOut: {
            /** Collection */
            collection: string;
            /** Description */
            description?: string | null;
            /** Favorite */
            favorite: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Note */
            note?: string | null;
            /** Queue Kind */
            queue_kind?: string | null;
            /** Read Status */
            read_status: string;
            /**
             * Saved At
             * Format: date-time
             */
            saved_at: string;
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
            /** Collection */
            collection?: string | null;
            /** Description */
            description?: string | null;
            /** Favorite */
            favorite?: boolean | null;
            /** Note */
            note?: string | null;
            /** Queue Kind */
            queue_kind?: string | null;
            /** Read Status */
            read_status?: string | null;
            /** Tags */
            tags?: string[] | null;
            /** Title */
            title?: string | null;
        };
        /**
         * CaptureIn
         * @description Extension ve Life OS ici quick capture ayni endpoint'i kullanir.
         */
        CaptureIn: {
            /** Client Uuid */
            client_uuid?: string | null;
            /**
             * Collection
             * @default inbox
             */
            collection: string;
            /** Description */
            description?: string | null;
            /** Note */
            note?: string | null;
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
            /** Rss Read */
            rss_read: number;
        };
        /** CollectionCount */
        CollectionCount: {
            /** Collection */
            collection: string;
            /** Count */
            count: number;
        };
        /** CourseIn */
        CourseIn: {
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
            /** Url */
            url?: string | null;
        };
        /** CoursePatch */
        CoursePatch: {
            /** Notes */
            notes?: string | null;
            /** Progress Pct */
            progress_pct?: number | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
        };
        /** DeadlineOut */
        DeadlineOut: {
            /**
             * Due At
             * Format: date-time
             */
            due_at: string;
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /** Module */
            module: string;
            /** Priority */
            priority: number;
            /** Sub Kind */
            sub_kind: string | null;
            /** Title */
            title: string;
            /** Type */
            type: string;
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
        /** FocusReviewStats */
        FocusReviewStats: {
            /** Interrupted */
            interrupted: number;
            /** Minutes */
            minutes: number;
            /** Sessions */
            sessions: number;
        };
        /** GithubCredentialsIn */
        GithubCredentialsIn: {
            /** Login */
            login: string;
            /** Token */
            token: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HabitCheck */
        HabitCheck: {
            /**
             * Day
             * Format: date
             */
            day?: string;
            /**
             * Done
             * @default true
             */
            done: boolean;
            /** Note */
            note?: string | null;
        };
        /** HabitGridEntry */
        HabitGridEntry: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Done */
            done: boolean;
            /**
             * Habit Id
             * Format: uuid
             */
            habit_id: string;
            /** Note */
            note?: string | null;
            /** Title */
            title: string;
        };
        /** HabitIn */
        HabitIn: {
            /**
             * Cadence
             * @default daily
             */
            cadence: string;
            /** Color */
            color?: string | null;
            /**
             * Position
             * @default 0
             */
            position: number;
            /**
             * Target Per Week
             * @default 7
             */
            target_per_week: number;
            /** Title */
            title: string;
        };
        /** HabitOut */
        HabitOut: {
            /** Active */
            active: boolean;
            /**
             * Best Streak
             * @default 0
             */
            best_streak: number;
            /** Cadence */
            cadence: string;
            /** Color */
            color: string | null;
            /**
             * Done Today
             * @default false
             */
            done_today: boolean;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Position */
            position: number;
            /**
             * Streak
             * @default 0
             */
            streak: number;
            /** Target Per Week */
            target_per_week: number;
            /** Title */
            title: string;
            /**
             * Week Done
             * @default 0
             */
            week_done: number;
        };
        /** HabitUpdate */
        HabitUpdate: {
            /** Active */
            active?: boolean | null;
            /** Cadence */
            cadence?: string | null;
            /** Color */
            color?: string | null;
            /** Position */
            position?: number | null;
            /** Target Per Week */
            target_per_week?: number | null;
            /** Title */
            title?: string | null;
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
            /** Created At */
            created_at?: string | null;
            /** Description */
            description?: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
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
        /** MediaDashboardOut */
        MediaDashboardOut: {
            /** Continue Items */
            continue_items: components["schemas"]["MediaItemOut"][];
            /** Recent Consumptions */
            recent_consumptions: components["schemas"]["MediaConsumptionOut"][];
            stats: components["schemas"]["MediaStats"];
            /** Upcoming */
            upcoming: components["schemas"]["MediaUnitOut"][];
        };
        /** MediaDetailOut */
        MediaDetailOut: {
            /** Collections */
            collections: components["schemas"]["MediaCollectionOut"][];
            /** Consumptions */
            consumptions: components["schemas"]["MediaConsumptionOut"][];
            /** Cycles */
            cycles: components["schemas"]["MediaCycleOut"][];
            item: components["schemas"]["MediaItemOut"];
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
            /** Last Run At */
            last_run_at?: string | null;
            /** Last Status */
            last_status?: string | null;
            /** Missing Settings */
            missing_settings: string[];
            /** Ready */
            ready: boolean;
        };
        /** MediaStats */
        MediaStats: {
            /** Average Score */
            average_score?: number | null;
            /** By Kind */
            by_kind: {
                [key: string]: number;
            };
            /** Completed */
            completed: number;
            /** In Progress */
            in_progress: number;
            /** Planned */
            planned: number;
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
        /** OpportunityOut */
        OpportunityOut: {
            /** Applied At */
            applied_at: string | null;
            /** Compensation */
            compensation: string | null;
            /** Deadline At */
            deadline_at: string | null;
            /** External Id */
            external_id: string | null;
            /**
             * Found At
             * Format: date-time
             */
            found_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Location */
            location: string | null;
            /** Notes */
            notes: string | null;
            /** Organization */
            organization: string | null;
            /** Priority */
            priority: number;
            /** Raw */
            raw: {
                [key: string]: unknown;
            };
            /** Remote */
            remote: string | null;
            /** Score */
            score?: number | null;
            /** Score Reasons */
            score_reasons?: {
                [key: string]: unknown;
            } | null;
            /** Source */
            source: string;
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
            /** Notes */
            notes?: string | null;
            /** Priority */
            priority?: number | null;
            /** Status */
            status?: string | null;
            /** Title */
            title?: string | null;
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
            /** Notes */
            notes?: string | null;
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
            /** Notes */
            notes?: string | null;
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
            /** Frequency */
            frequency?: string | null;
            /** Next Due At */
            next_due_at?: string | null;
            /** Note */
            note?: string | null;
            /** Title */
            title?: string | null;
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
        /** ReviewIn */
        ReviewIn: {
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
        ReviewOut: {
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
        /** ReviewPreview */
        ReviewPreview: {
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
        /** ReviewStats */
        ReviewStats: {
            capture: components["schemas"]["CaptureReviewStats"];
            focus: components["schemas"]["FocusReviewStats"];
            /** Habits */
            habits: {
                [key: string]: number;
            };
            todos: components["schemas"]["TodoReviewStats"];
            /** Topics */
            topics: components["schemas"]["TopicReviewStats"][];
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
        /** SaveItemIn */
        SaveItemIn: {
            /**
             * Collection
             * @default read_later
             */
            collection: string;
        };
        /** SavedViewIn */
        SavedViewIn: {
            /**
             * Filter
             * @default {}
             */
            filter: {
                [key: string]: unknown;
            };
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
        /** SettingIn */
        SettingIn: {
            /** Value */
            value: unknown;
        };
        /**
         * SourceRefreshIn
         * @description Bos govde = katalogun tamami.
         */
        SourceRefreshIn: {
            /** Kind */
            kind?: ("job" | "announcement") | null;
            /** Source Ids */
            source_ids?: string[] | null;
        };
        /** SourceRefreshOut */
        SourceRefreshOut: {
            /** Batch Id */
            batch_id: string | null;
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
            /** Milestone Id */
            milestone_id?: string | null;
            /** Milestone Title */
            milestone_title?: string | null;
            /** Parent Id */
            parent_id: string | null;
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
        /** TopicPatch */
        TopicPatch: {
            /** Confidence */
            confidence?: number | null;
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
        /** TopicReviewStats */
        TopicReviewStats: {
            /** Minutes */
            minutes: number;
            /** Topic */
            topic: string;
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
                since?: string | null;
                verbs?: string[] | null;
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
    collections_api_bookmarks_collections_get: {
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
                    "application/json": string[];
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
    books_api_books_get: {
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
    add_book_api_books_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BookIn"];
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
    delete_book_api_books__id__delete: {
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
    patch_book_api_books__id__patch: {
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
                "application/json": components["schemas"]["BookPatch"];
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
    courses_api_courses_get: {
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
    delete_course_api_courses__id__delete: {
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
    patch_course_api_courses__id__patch: {
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
    deadlines_api_deadlines_get: {
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
                    "application/json": components["schemas"]["DeadlineOut"][];
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
                    "application/json": components["schemas"]["EntityOut"][];
                };
            };
            /** @description Validation Error */
            422: {
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
    summary_api_expenses_summary_get: {
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
    github_activity_api_github_activity_get: {
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
    sync_github_api_github_sync_post: {
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
    list_habits_api_habits_get: {
        parameters: {
            query?: {
                active?: boolean | null;
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
                    "application/json": components["schemas"]["HabitOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_habit_api_habits_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HabitIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HabitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    habit_grid_api_habits_grid_get: {
        parameters: {
            query?: {
                weeks?: number;
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
                    "application/json": components["schemas"]["HabitGridEntry"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_habit_api_habits__habit_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                habit_id: string;
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
    update_habit_api_habits__habit_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                habit_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HabitUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HabitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    check_habit_api_habits__habit_id__check_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                habit_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HabitCheck"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HabitOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    queue_api_learning_queue_get: {
        parameters: {
            query?: {
                kind?: string | null;
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
                monitored?: boolean | null;
                trashed?: boolean;
                sort?: "updated" | "created" | "title" | "score" | "progress";
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
                    "application/json": components["schemas"]["MediaDashboardOut"];
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
    search_metadata_api_media_search_get: {
        parameters: {
            query: {
                q: string;
                kind: string;
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
                    "application/json": components["schemas"]["MetadataResult"][];
                };
            };
            /** @description Validation Error */
            422: {
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
                    "application/json": components["schemas"]["MediaStats"];
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
                    "application/json": components["schemas"]["MediaUnitOut"][];
                };
            };
            /** @description Validation Error */
            422: {
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
                    "application/json": components["schemas"]["MediaConsumptionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
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
    project_timeline_api_projects__project_id__timeline_get: {
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
                    "application/json": components["schemas"]["ReviewOut"][];
                };
            };
            /** @description Validation Error */
            422: {
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
                "application/json": components["schemas"]["ReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewOut"];
                };
            };
            /** @description Validation Error */
            422: {
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
                    "application/json": components["schemas"]["SourceRefreshOut"];
                };
            };
            /** @description Validation Error */
            422: {
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
    areas_api_study_areas_get: {
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
    stale_api_study_stale_get: {
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
    stats_api_study_topics__topic_id__stats_get: {
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
                "application/json": components["schemas"]["SavedViewIn"];
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
