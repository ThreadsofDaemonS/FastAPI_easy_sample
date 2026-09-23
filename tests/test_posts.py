import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str = "author@example.com") -> str:
    await client.post("/users/register", json={"email": email, "password": "strongpass123"})
    login = await client.post(
        "/users/login", data={"username": email, "password": "strongpass123"}
    )
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_get_post(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/posts/", json={"title": "Hello", "body": "World"}, headers=headers
    )
    assert create_response.status_code == 201
    post_id = create_response.json()["id"]

    get_response = await client.get(f"/posts/{post_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["title"] == "Hello"
    assert body["author"]["email"] == "author@example.com"  # eager-loaded author, без N+1


@pytest.mark.asyncio
async def test_get_missing_post_returns_404(client: AsyncClient) -> None:
    response = await client.get("/posts/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_view_counter_increments_atomically(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/posts/", json={"title": "Views", "body": "Body"}, headers=headers
    )
    post_id = created.json()["id"]

    await client.get(f"/posts/{post_id}")
    second = await client.get(f"/posts/{post_id}")

    assert second.json()["views"] == 2


@pytest.mark.asyncio
async def test_list_posts_pagination_and_cache(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(3):
        await client.post(
            "/posts/", json={"title": f"Post {i}", "body": "..."}, headers=headers
        )

    first_page = await client.get("/posts/?limit=2")
    assert first_page.status_code == 200
    page = first_page.json()
    assert len(page["items"]) == 2
    assert page["next_cursor"] is not None

    # другий виклик з тими самими параметрами має піти з Redis-кешу, а не з БД
    cached_page = await client.get("/posts/?limit=2")
    assert cached_page.json() == page

    second_page = await client.get(f"/posts/?limit=2&cursor={page['next_cursor']}")
    assert len(second_page.json()["items"]) == 1


@pytest.mark.asyncio
async def test_create_post_invalidates_list_cache(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/posts/", json={"title": "First", "body": "..."}, headers=headers)
    first_list = await client.get("/posts/")
    assert len(first_list.json()["items"]) == 1

    await client.post("/posts/", json={"title": "Second", "body": "..."}, headers=headers)
    second_list = await client.get("/posts/")
    assert len(second_list.json()["items"]) == 2


@pytest.mark.asyncio
async def test_export_csv(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/posts/", json={"title": "Csv,Row", "body": "..."}, headers=headers)

    response = await client.get("/posts/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.startswith("id,title,author_id,views,created_at\n")
