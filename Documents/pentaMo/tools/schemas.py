from pydantic import BaseModel, Field
from typing import Optional, List

class SearchListingsSchema(BaseModel):
    brands: Optional[List[str]] = Field(None, description="Danh sách hãng xe cần tìm")
    price_min: Optional[float] = Field(None, description="Giá thấp nhất (VNĐ)")
    price_max: Optional[float] = Field(None, description="Giá cao nhất (VNĐ)")
    province: Optional[str] = Field(None, description="Tỉnh/Thành phố")
    year_min: Optional[int] = Field(None, description="Đời xe thấp nhất")
    condition: Optional[str] = Field(None, description="Tình trạng (New, Used, Like New)")
    query_str: Optional[str] = Field(None, description="Từ khóa tìm kiếm chung")

class BookAppointmentSchema(BaseModel):
    listing_id: str = Field(..., description="ID của tin đăng xe")
    preferred_date: Optional[str] = Field(None, description="Ngày hẹn dự kiến (ISO 8601)")
    preferred_location: Optional[str] = Field(None, description="Địa điểm xem xe")

class CreateChatChannelSchema(BaseModel):
    listing_id: str = Field(..., description="ID của tin đăng xe")
    buyer_id: str = Field(..., description="ID người mua")
    seller_id: str = Field(..., description="ID người bán")

class DetectRisksSchema(BaseModel):
    text: str = Field(..., description="Nội dung tin nhắn cần kiểm tra rủi ro")
    conversation_id: str = Field(..., description="ID cuộc hội thoại")
