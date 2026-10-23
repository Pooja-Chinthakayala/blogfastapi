from tests.conftest import register_user, token_for, auth_headers

def test_author_creates_draft_and_publishes(client):
    register_user(client, "Author", "author@example.com", role="author")
    token = token_for(client, "author@example.com")
    headers = auth_headers(token)
    created = client.post("/posts", json={"title": "Hello", "content": "Blog body"}, headers=headers)
    assert created.status_code == 201
    post = created.json()
    assert post["status"] == "draft"
    assert client.get("/posts").json()["total"] == 0
    published = client.patch(f"/posts/{post['id']}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert client.get("/posts").json()["total"] == 1

def test_reader_cannot_create_post(client):
    register_user(client, "Reader", "reader@example.com")
    token = token_for(client, "reader@example.com")
    response = client.post("/posts", json={"title": "No", "content": "No"}, headers=auth_headers(token))
    assert response.status_code == 403

def test_author_cannot_manage_another_authors_post(client):
    register_user(client, "Author One", "one@example.com", role="author")
    register_user(client, "Author Two", "two@example.com", role="author")
    token1 = token_for(client, "one@example.com")
    token2 = token_for(client, "two@example.com")
    post = client.post("/posts", json={"title": "Owned", "content": "Body"},
                       headers=auth_headers(token1)).json()
    response = client.put(f"/posts/{post['id']}", json={"title": "Hijack"},
                          headers=auth_headers(token2))
    assert response.status_code == 403
