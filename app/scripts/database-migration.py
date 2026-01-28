#!/usr/bin/env python3
"""
Database migration strategy for Blue-Green deployments
"""

import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
from typing import List, Dict
from alembic.config import Config
from alembic import command

class DatabaseMigrator:
    def __init__(self, primary_db_url: str, replica_db_url: str = None):
        self.primary_db_url = primary_db_url
        self.replica_db_url = replica_db_url or primary_db_url
    
    def check_database_compatibility(self) -> Dict:
        """Check if database schema is compatible with new version"""
        checks = {
            'schema_version': self.get_schema_version(),
            'pending_migrations': self.get_pending_migrations(),
            'data_consistency': self.check_data_consistency(),
            'backup_exists': self.check_backup_exists(),
        }
        
        return checks
    
    def get_schema_version(self) -> str:
        """Get current schema version"""
        conn = psycopg2.connect(self.primary_db_url)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT version_num FROM alembic_version")
            result = cursor.fetchone()
            return result[0] if result else "unknown"
        except:
            return "unknown"
        finally:
            cursor.close()
            conn.close()
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations"""
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.primary_db_url)
        
        try:
            # Get current revision
            current = command.current(alembic_cfg)
            
            # Get available migrations
            available = command.heads(alembic_cfg)
            
            # Compare to find pending
            # This is simplified - in reality, you'd parse the revisions
            return []
        except:
            return []
    
    def check_data_consistency(self) -> bool:
        """Check data consistency between primary and replica"""
        if self.primary_db_url == self.replica_db_url:
            return True
        
        queries = [
            "SELECT COUNT(*) FROM students",
            "SELECT COUNT(*) FROM universities",
            "SELECT COUNT(*) FROM generated_papers",
        ]
        
        try:
            conn1 = psycopg2.connect(self.primary_db_url)
            conn2 = psycopg2.connect(self.replica_db_url)
            
            cursor1 = conn1.cursor()
            cursor2 = conn2.cursor()
            
            for query in queries:
                cursor1.execute(query)
                cursor2.execute(query)
                
                count1 = cursor1.fetchone()[0]
                count2 = cursor2.fetchone()[0]
                
                if count1 != count2:
                    print(f"Data mismatch in {query}: {count1} != {count2}")
                    return False
            
            cursor1.close()
            cursor2.close()
            conn1.close()
            conn2.close()
            
            return True
        except Exception as e:
            print(f"Error checking data consistency: {e}")
            return False
    
    def check_backup_exists(self) -> bool:
        """Check if recent backup exists"""
        # In production, check S3 or backup service
        return True
    
    def run_migrations(self, target_revision: str = "head") -> bool:
        """Run database migrations"""
        print(f"Running migrations to revision: {target_revision}")
        
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.primary_db_url)
        
        try:
            # Run migrations
            command.upgrade(alembic_cfg, target_revision)
            
            # Verify migration
            current = command.current(alembic_cfg)
            print(f"Migrations completed. Current version: {current}")
            
            return True
        except Exception as e:
            print(f"Migration failed: {e}")
            return False
    
    def rollback_migrations(self, target_revision: str) -> bool:
        """Rollback migrations"""
        print(f"Rolling back migrations to revision: {target_revision}")
        
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.primary_db_url)
        
        try:
            command.downgrade(alembic_cfg, target_revision)
            print("Rollback completed")
            return True
        except Exception as e:
            print(f"Rollback failed: {e}")
            return False
    
    def create_readonly_user(self, username: str, password: str) -> bool:
        """Create readonly user for blue/green environments"""
        conn = psycopg2.connect(self.primary_db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            # Create user if not exists
            cursor.execute(f"""
                DO $$
                BEGIN
                  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{username}') THEN
                    CREATE USER {username} WITH PASSWORD '{password}';
                  END IF;
                END
                $$;
            """)
            
            # Grant readonly permissions
            cursor.execute(f"""
                GRANT CONNECT ON DATABASE {conn.info.dbname} TO {username};
                GRANT USAGE ON SCHEMA public TO {username};
                GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                GRANT SELECT ON TABLES TO {username};
            """)
            
            print(f"Readonly user {username} created/updated")
            return True
        except Exception as e:
            print(f"Error creating readonly user: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def prepare_database_for_deployment(self, deployment_color: str) -> bool:
        """Prepare database for blue/green deployment"""
        print(f"Preparing database for {deployment_color} deployment")
        
        # 1. Check compatibility
        checks = self.check_database_compatibility()
        if not all(checks.values()):
            print("Database compatibility checks failed:")
            for check, result in checks.items():
                print(f"  {check}: {result}")
            return False
        
        # 2. Create deployment-specific user
        username = f"app_{deployment_color}"
        password = f"password_{deployment_color}_{int(time.time())}"
        
        if not self.create_readonly_user(username, password):
            return False
        
        # 3. Run migrations if needed
        if checks['pending_migrations']:
            print("Pending migrations found, running...")
            if not self.run_migrations():
                return False
        
        print("Database preparation completed")
        return True

def main():
    parser = argparse.ArgumentParser(description="Database migration for Blue-Green")
    parser.add_argument("--db-url", required=True, help="Primary database URL")
    parser.add_argument("--replica-url", help="Replica database URL")
    parser.add_argument("--action", required=True,
                       choices=["check", "migrate", "rollback", "prepare"],
                       help="Action to perform")
    parser.add_argument("--target-revision", help="Target migration revision")
    parser.add_argument("--deployment-color", help="Deployment color (blue/green)")
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator(args.db_url, args.replica_url)
    
    if args.action == "check":
        checks = migrator.check_database_compatibility()
        print("Database Compatibility Check:")
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}: {result}")
    
    elif args.action == "migrate":
        if not args.target_revision:
            print("Error: --target-revision is required for migrate")
            return
        
        if migrator.run_migrations(args.target_revision):
            print("✅ Migration successful")
        else:
            print("❌ Migration failed")
    
    elif args.action == "rollback":
        if not args.target_revision:
            print("Error: --target-revision is required for rollback")
            return
        
        if migrator.rollback_migrations(args.target_revision):
            print("✅ Rollback successful")
        else:
            print("❌ Rollback failed")
    
    elif args.action == "prepare":
        if not args.deployment_color:
            print("Error: --deployment-color is required for prepare")
            return
        
        if migrator.prepare_database_for_deployment(args.deployment_color):
            print("✅ Database preparation successful")
        else:
            print("❌ Database preparation failed")

if __name__ == "__main__":
    main()