import { sql } from '@vercel/postgres';

export default async function handler(req, res) {
  try {
    // DB에서 모든 로그를 가져옴 (최신순)
    const { rows } = await sql`SELECT * FROM logs ORDER BY id DESC`;
    
    // 브라우저에 로그 목록을 뿌려줌
    res.status(200).json(rows);
  } catch (error) {
    res.status(500).json({ error: "로그를 불러올 수 없습니다." });
  }
}