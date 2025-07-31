"""
Swagger UI 커스터마이징 유틸리티
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI):
    """Swagger UI 커스터마이징을 위한 custom_openapi 함수"""

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Swagger UI 커스터마이징
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
        "altText": "FileWallBall API",
    }

    # Swagger UI 테마 설정
    openapi_schema["info"]["x-tagGroups"] = [
        {
            "name": "파일 관리",
            "tags": ["파일 업로드", "파일 관리", "파일 검색", "썸네일"],
        },
        {
            "name": "시스템 관리",
            "tags": ["인증 및 권한", "모니터링", "관리자", "백그라운드 작업"],
        },
    ]

    # Swagger UI 설정
    openapi_schema["x-swagger-ui"] = {
        "docExpansion": "list",
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 1,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True,
        "requestInterceptor": """
        function(request) {
            // 요청 인터셉터 - 토큰 자동 추가
            if (request.headers && request.headers.Authorization) {
                console.log('Authorization header found:', request.headers.Authorization);
            }
            return request;
        }
        """,
        "responseInterceptor": """
        function(response) {
            // 응답 인터셉터 - 에러 처리
            if (response.status >= 400) {
                console.error('API Error:', response.status, response.body);
            }
            return response;
        }
        """,
    }

    # ReDoc 설정
    openapi_schema["x-redoc"] = {
        "theme": {
            "colors": {"primary": {"main": "#1976d2"}},
            "typography": {"fontSize": "14px", "lineHeight": "1.5em"},
        },
        "hideDownloadButton": False,
        "hideHostname": False,
        "hideLoading": False,
        "nativeScrollbars": False,
        "pathInMiddlePanel": True,
        "requiredPropsFirst": True,
        "scrollYOffset": 0,
        "showExtensions": True,
        "sortPropsAlphabetically": True,
        "suppressWarnings": False,
        "theme": {"spacing": {"sectionVertical": 15}},
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_swagger_ui_html():
    """커스터마이징된 Swagger UI HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FileWallBall API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
        <style>
            html {
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }
            *, *:before, *:after {
                box-sizing: inherit;
            }
            body {
                margin:0;
                background: #fafafa;
            }
            .swagger-ui .topbar {
                background-color: #1976d2;
            }
            .swagger-ui .topbar .download-url-wrapper .select-label {
                color: white;
            }
            .swagger-ui .topbar .download-url-wrapper input[type=text] {
                border: 2px solid white;
                color: #1976d2;
            }
            .swagger-ui .info .title {
                color: #1976d2;
            }
            .swagger-ui .opblock.opblock-get .opblock-summary-method {
                background: #61affe;
            }
            .swagger-ui .opblock.opblock-post .opblock-summary-method {
                background: #49cc90;
            }
            .swagger-ui .opblock.opblock-put .opblock-summary-method {
                background: #fca130;
            }
            .swagger-ui .opblock.opblock-delete .opblock-summary-method {
                background: #f93e3e;
            }
            .swagger-ui .btn.execute {
                background-color: #1976d2;
            }
            .swagger-ui .btn.execute:hover {
                background-color: #1565c0;
            }
            .swagger-ui .auth-wrapper .authorize {
                background-color: #1976d2;
                border-color: #1976d2;
            }
            .swagger-ui .auth-wrapper .authorize:hover {
                background-color: #1565c0;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                const ui = SwaggerUIBundle({
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout",
                    docExpansion: "list",
                    defaultModelsExpandDepth: 1,
                    defaultModelExpandDepth: 1,
                    displayRequestDuration: true,
                    filter: true,
                    showExtensions: true,
                    showCommonExtensions: true,
                    tryItOutEnabled: true,
                    requestInterceptor: function(request) {
                        // 요청 인터셉터 - 토큰 자동 추가
                        if (request.headers && request.headers.Authorization) {
                            console.log('Authorization header found:', request.headers.Authorization);
                        }
                        return request;
                    },
                    responseInterceptor: function(response) {
                        // 응답 인터셉터 - 에러 처리
                        if (response.status >= 400) {
                            console.error('API Error:', response.status, response.body);
                        }
                        return response;
                    }
                });

                // 커스텀 이벤트 리스너
                ui.initOAuth({
                    clientId: "filewallball-api",
                    clientSecret: "your-client-secret",
                    realm: "filewallball",
                    appName: "FileWallBall API",
                    scopes: "read write",
                    additionalQueryStringParams: {},
                    useBasicAuthenticationWithAccessCodeGrant: false,
                    usePkceWithAuthorizationCodeGrant: false
                });
            };
        </script>
    </body>
    </html>
    """


def get_redoc_html():
    """커스터마이징된 ReDoc HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FileWallBall API Documentation - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {
                margin: 0;
                padding: 0;
            }
        </style>
    </head>
    <body>
        <div id="redoc"></div>
        <script src="https://unpkg.com/redoc@2.1.3/bundles/redoc.standalone.js"></script>
        <script>
            Redoc.init('/openapi.json', {
                theme: {
                    colors: {
                        primary: {
                            main: '#1976d2'
                        }
                    },
                    typography: {
                        fontSize: '14px',
                        lineHeight: '1.5em',
                        fontFamily: 'Roboto, sans-serif',
                        headings: {
                            fontFamily: 'Montserrat, sans-serif',
                            fontWeight: '400'
                        }
                    },
                    sidebar: {
                        backgroundColor: '#fafafa'
                    }
                },
                hideDownloadButton: false,
                hideHostname: false,
                hideLoading: false,
                nativeScrollbars: false,
                pathInMiddlePanel: true,
                requiredPropsFirst: true,
                scrollYOffset: 0,
                showExtensions: true,
                sortPropsAlphabetically: true,
                suppressWarnings: false,
                theme: {
                    spacing: {
                        sectionVertical: 15
                    }
                }
            }, document.getElementById('redoc'));
        </script>
    </body>
    </html>
    """


def get_api_examples():
    """API 사용 예제 데이터"""
    return {
        "file_upload_example": {
            "summary": "파일 업로드 예제",
            "description": "PDF 문서 업로드 예제",
            "value": {
                "file": "(binary file data)",
                "category_id": 1,
                "tags": ["document", "pdf", "important"],
                "is_public": True,
                "description": "분기별 실적 보고서",
            },
        },
        "file_download_example": {
            "summary": "파일 다운로드 예제",
            "description": "Range 요청을 사용한 부분 다운로드",
            "headers": {
                "Range": "bytes=0-1023",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            },
        },
        "auth_token_example": {
            "summary": "JWT 토큰 예제",
            "description": "유효한 JWT Bearer 토큰",
            "value": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwidXNlcl9pZCI6IjEyMyIsInBlcm1pc3Npb25zIjpbImZpbGVfcmVhZCIsImZpbGVfd3JpdGUiXSwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        },
        "error_response_example": {
            "summary": "에러 응답 예제",
            "description": "파일을 찾을 수 없는 경우의 에러 응답",
            "value": {
                "detail": "파일을 찾을 수 없습니다.",
                "error_type": "not_found",
                "error_code": 404,
                "timestamp": "2024-01-15T10:30:00Z",
            },
        },
    }


def get_curl_examples():
    """cURL 명령어 예제"""
    return {
        "upload_file": {
            "summary": "파일 업로드",
            "description": "cURL을 사용한 파일 업로드",
            "command": """curl -X POST "http://localhost:8000/upload" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -F "file=@document.pdf" \\
     -F "category_id=1" \\
     -F "tags=document,pdf" \\
     -F "is_public=true" \\
     -F "description=중요한 문서\"""",
        },
        "download_file": {
            "summary": "파일 다운로드",
            "description": "cURL을 사용한 파일 다운로드",
            "command": """curl -X GET "http://localhost:8000/download/{file_id}" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -o "downloaded_file.pdf\"""",
        },
        "get_file_info": {
            "summary": "파일 정보 조회",
            "description": "cURL을 사용한 파일 정보 조회",
            "command": """curl -X GET "http://localhost:8000/files/{file_id}" \\
     -H "Authorization: Bearer YOUR_TOKEN" \\
     -H "Content-Type: application/json\"""",
        },
        "health_check": {
            "summary": "헬스체크",
            "description": "cURL을 사용한 헬스체크",
            "command": """curl -X GET "http://localhost:8000/health" \\
     -H "Content-Type: application/json\"""",
        },
    }


def get_code_examples():
    """프로그래밍 언어별 코드 예제"""
    return {
        "python": {
            "summary": "Python 예제",
            "description": "requests 라이브러리를 사용한 Python 예제",
            "code": """
import requests

# 파일 업로드
def upload_file(file_path, token):
    url = "http://localhost:8000/upload"
    headers = {"Authorization": f"Bearer {token}"}

    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'category_id': 1,
            'tags': 'document,pdf',
            'is_public': True,
            'description': '중요한 문서'
        }
        response = requests.post(url, headers=headers, files=files, data=data)
        return response.json()

# 파일 다운로드
def download_file(file_id, token, output_path):
    url = f"http://localhost:8000/download/{file_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    with open(output_path, 'wb') as f:
        f.write(response.content)
""",
        },
        "javascript": {
            "summary": "JavaScript 예제",
            "description": "fetch API를 사용한 JavaScript 예제",
            "code": """
// 파일 업로드
async function uploadFile(file, token) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category_id', '1');
    formData.append('tags', 'document,pdf');
    formData.append('is_public', 'true');
    formData.append('description', '중요한 문서');

    const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData
    });

    return await response.json();
}

// 파일 다운로드
async function downloadFile(fileId, token) {
    const response = await fetch(`http://localhost:8000/download/${fileId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'downloaded_file.pdf';
    a.click();
}
""",
        },
        "java": {
            "summary": "Java 예제",
            "description": "OkHttp를 사용한 Java 예제",
            "code": """
import okhttp3.*;
import java.io.File;

public class FileWallBallClient {
    private final OkHttpClient client = new OkHttpClient();
    private final String baseUrl = "http://localhost:8000";
    private final String token;

    public FileWallBallClient(String token) {
        this.token = token;
    }

    // 파일 업로드
    public String uploadFile(File file) throws Exception {
        RequestBody requestBody = new MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", file.getName(),
                RequestBody.create(MediaType.parse("application/octet-stream"), file))
            .addFormDataPart("category_id", "1")
            .addFormDataPart("tags", "document,pdf")
            .addFormDataPart("is_public", "true")
            .addFormDataPart("description", "중요한 문서")
            .build();

        Request request = new Request.Builder()
            .url(baseUrl + "/upload")
            .addHeader("Authorization", "Bearer " + token)
            .post(requestBody)
            .build();

        try (Response response = client.newCall(request).execute()) {
            return response.body().string();
        }
    }
}
""",
        },
    }
