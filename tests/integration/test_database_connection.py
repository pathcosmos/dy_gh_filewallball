#!/usr/bin/env python3
"""
MariaDB 연결 테스트 스크립트
"""

from datetime import datetime

import pymysql


def test_database_connection():
    """MariaDB 연결 및 기본 기능 테스트"""
    try:
        # 데이터베이스 연결
        print("🔍 MariaDB 연결 테스트 중...")
        connection = pymysql.connect(
            host="localhost",
            port=3306,
            user="filewallball_user",
            password="filewallball_user_pass",
            database="filewallball_db",
            charset="utf8mb4",
        )

        print("✅ MariaDB 연결 성공!")

        with connection.cursor() as cursor:
            # 데이터베이스 정보 조회
            print("\n📊 데이터베이스 정보...")
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ MariaDB 버전: {version[0]}")

            # 테이블 목록 조회
            print("\n📋 테이블 목록...")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ 테이블 개수: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")

            # 파일 테이블 구조 확인
            print("\n📁 files 테이블 구조...")
            cursor.execute("DESCRIBE files")
            columns = cursor.fetchall()
            print("✅ files 테이블 컬럼:")
            for column in columns:
                print(f"  - {column[0]}: {column[1]}")

            # 샘플 데이터 삽입 테스트
            print("\n📝 샘플 데이터 삽입 테스트...")
            test_filename = f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            # file_extensions 테이블에 확장자 추가
            cursor.execute(
                """
                INSERT IGNORE INTO file_extensions (extension, mime_type, is_allowed)
                VALUES ('.txt', 'text/plain', 1)
            """
            )

            # files 테이블에 테스트 데이터 삽입 (실제 구조에 맞게 수정)
            cursor.execute(
                """
                INSERT INTO files (file_uuid, original_filename, stored_filename,
                                 file_extension, mime_type, file_size, file_hash,
                                 storage_path, is_public, is_deleted, created_at, updated_at)
                VALUES (UUID(), %s, %s, '.txt', 'text/plain', 1024,
                       'd41d8cd98f00b204e9800998ecf8427e', '/test/path', 1, 0, NOW(), NOW())
            """,
                (test_filename, test_filename),
            )

            file_id = cursor.lastrowid
            print(f"✅ 테스트 파일 삽입 완료: ID={file_id}")

            # 삽입된 데이터 조회
            cursor.execute(
                """
                SELECT file_uuid, original_filename, file_size, created_at,
                       file_extension, mime_type
                FROM files
                WHERE id = %s
            """,
                (file_id,),
            )

            result = cursor.fetchone()
            if result:
                print(f"✅ 데이터 조회 성공: {result[1]} ({result[4]})")

            # 테스트 데이터 정리
            cursor.execute("DELETE FROM files WHERE id = %s", (file_id,))
            print("✅ 테스트 데이터 정리 완료")

            connection.commit()

        connection.close()
        return True

    except pymysql.Error as e:
        print(f"❌ MariaDB 연결 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 중 오류 발생: {e}")
        return False


if __name__ == "__main__":
    print("🚀 MariaDB 연결 테스트 시작\n")
    success = test_database_connection()

    if success:
        print("\n🎉 모든 MariaDB 테스트가 성공했습니다!")
    else:
        print("\n💥 MariaDB 테스트에 실패했습니다.")
