export default function handler(req, res) {
  // 주소창에서 a와 b를 가져옴
  const { a, b } = req.query;
  
  const sum = Number(a) + Number(b);
  
  // 결과를 JSON 형태로 응답함
  res.status(200).json({ result: sum });
}