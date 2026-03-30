import { sql } from '@vercel/postgres';

export default function handler(req, res) {
  // 주소창에서 a와 b를 가져옴
  const { a, b } = req.query;
  
  const num1 = Number(a);
  const num2 = Number(b);
  const sum = num1 + num2;

  try {
    // DB에 로그 저장
    await sql`
      INSERT INTO logs (num1, num2, result)
      VALUES (${num1}, ${num2}, ${sum});
    `;

    // 3. 결과 응답
    res.status(200).json({ 
      result: sum
    });
  } catch (error) {
    // DB 연결 실패 시 에러 출력
    console.error(error);
    res.status(500).json({ error: "DB 저장에 실패했습니다." });
  }
}