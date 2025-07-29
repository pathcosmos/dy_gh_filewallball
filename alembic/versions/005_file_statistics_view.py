"""Task 8.5: Create file_statistics view

Revision ID: 005
Revises: 004
Create Date: 2025-07-29 06:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """
    Task 8.5: Create file_statistics view for efficient file statistics aggregation
    
    This view aggregates data from file_views and file_downloads tables to provide
    comprehensive statistics for each file including:
    - Total view count
    - Total download count
    - Last viewed timestamp
    - Last downloaded timestamp
    - Average views per day
    - Popularity score
    """
    
    # Task 8.5: Create file_statistics view
    op.execute("""
        CREATE OR REPLACE VIEW file_statistics AS
        SELECT 
            f.file_uuid,
            f.id as file_id,
            f.original_filename,
            f.file_extension,
            f.file_size,
            f.is_public,
            f.created_at,
            f.updated_at,
            
            -- View statistics
            COALESCE(v_stats.view_count, 0) as total_views,
            COALESCE(v_stats.unique_viewers, 0) as unique_viewers,
            COALESCE(v_stats.last_viewed, f.created_at) as last_viewed,
            COALESCE(v_stats.first_viewed, f.created_at) as first_viewed,
            
            -- Download statistics
            COALESCE(d_stats.download_count, 0) as total_downloads,
            COALESCE(d_stats.unique_downloaders, 0) as unique_downloaders,
            COALESCE(d_stats.last_downloaded, NULL) as last_downloaded,
            COALESCE(d_stats.first_downloaded, NULL) as first_downloaded,
            COALESCE(d_stats.total_bytes_downloaded, 0) as total_bytes_downloaded,
            
            -- Calculated statistics
            COALESCE(v_stats.view_count, 0) + COALESCE(d_stats.download_count, 0) as total_interactions,
            
            -- Popularity score (views + downloads * 2, weighted by recency)
            CASE 
                WHEN f.created_at > DATE_SUB(NOW(), INTERVAL 7 DAY) THEN
                    (COALESCE(v_stats.view_count, 0) + COALESCE(d_stats.download_count, 0) * 2) * 1.5
                WHEN f.created_at > DATE_SUB(NOW(), INTERVAL 30 DAY) THEN
                    (COALESCE(v_stats.view_count, 0) + COALESCE(d_stats.download_count, 0) * 2) * 1.2
                ELSE
                    COALESCE(v_stats.view_count, 0) + COALESCE(d_stats.download_count, 0) * 2
            END as popularity_score,
            
            -- Daily average views (last 30 days)
            CASE 
                WHEN DATEDIFF(NOW(), f.created_at) > 0 THEN
                    COALESCE(v_stats.view_count, 0) / GREATEST(DATEDIFF(NOW(), f.created_at), 1)
                ELSE 0
            END as avg_daily_views,
            
            -- Engagement rate (downloads / views)
            CASE 
                WHEN COALESCE(v_stats.view_count, 0) > 0 THEN
                    COALESCE(d_stats.download_count, 0) / v_stats.view_count
                ELSE 0
            END as engagement_rate,
            
            -- Recent activity (last 7 days)
            COALESCE(v_stats.recent_views, 0) as recent_views,
            COALESCE(d_stats.recent_downloads, 0) as recent_downloads,
            
            -- View type breakdown
            COALESCE(v_stats.info_views, 0) as info_views,
            COALESCE(v_stats.preview_views, 0) as preview_views,
            COALESCE(v_stats.thumbnail_views, 0) as thumbnail_views,
            
            -- Timestamps
            NOW() as statistics_updated_at
            
        FROM files f
        
        -- Left join with view statistics
        LEFT JOIN (
            SELECT 
                fv.file_uuid,
                COUNT(*) as view_count,
                COUNT(DISTINCT fv.user_id) as unique_viewers,
                MAX(fv.viewed_at) as last_viewed,
                MIN(fv.viewed_at) as first_viewed,
                COUNT(CASE WHEN fv.viewed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as recent_views,
                COUNT(CASE WHEN fv.view_type = 'info' THEN 1 END) as info_views,
                COUNT(CASE WHEN fv.view_type = 'preview' THEN 1 END) as preview_views,
                COUNT(CASE WHEN fv.view_type = 'thumbnail' THEN 1 END) as thumbnail_views
            FROM file_views fv
            WHERE fv.file_uuid IS NOT NULL
            GROUP BY fv.file_uuid
        ) v_stats ON f.file_uuid = v_stats.file_uuid
        
        -- Left join with download statistics
        LEFT JOIN (
            SELECT 
                fd.file_uuid,
                COUNT(*) as download_count,
                COUNT(DISTINCT fd.user_id) as unique_downloaders,
                MAX(fd.downloaded_at) as last_downloaded,
                MIN(fd.downloaded_at) as first_downloaded,
                SUM(fd.bytes_downloaded) as total_bytes_downloaded,
                COUNT(CASE WHEN fd.downloaded_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as recent_downloads
            FROM file_downloads fd
            WHERE fd.file_uuid IS NOT NULL
            GROUP BY fd.file_uuid
        ) d_stats ON f.file_uuid = d_stats.file_uuid
        
        WHERE f.is_deleted = FALSE
        ORDER BY popularity_score DESC, f.created_at DESC
    """)
    
    # Task 8.5: Create indexes for better view performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_views_file_uuid_viewed_at 
        ON file_views(file_uuid, viewed_at)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_downloads_file_uuid_downloaded_at 
        ON file_downloads(file_uuid, downloaded_at)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_views_view_type 
        ON file_views(view_type)
    """)
    
    # Task 8.5: Create materialized view for frequently accessed statistics
    op.execute("""
        CREATE TABLE file_statistics_cache (
            file_uuid VARCHAR(36) PRIMARY KEY,
            total_views INT DEFAULT 0,
            total_downloads INT DEFAULT 0,
            last_viewed TIMESTAMP NULL,
            last_downloaded TIMESTAMP NULL,
            popularity_score DECIMAL(10,2) DEFAULT 0,
            cache_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_popularity_score (popularity_score DESC),
            INDEX idx_cache_updated_at (cache_updated_at)
        ) ENGINE=InnoDB
    """)


def downgrade():
    """
    Task 8.5: Drop file_statistics view and related indexes
    """
    
    # Drop materialized view cache table
    op.execute("DROP TABLE IF EXISTS file_statistics_cache")
    
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_file_views_file_uuid_viewed_at ON file_views")
    op.execute("DROP INDEX IF EXISTS idx_file_downloads_file_uuid_downloaded_at ON file_downloads")
    op.execute("DROP INDEX IF EXISTS idx_file_views_view_type ON file_views")
    
    # Drop view
    op.execute("DROP VIEW IF EXISTS file_statistics") 