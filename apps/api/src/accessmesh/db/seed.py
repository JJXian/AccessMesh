import asyncio

from sqlalchemy import select

from accessmesh.db.models import DemoUser, Resource
from accessmesh.db.session import AsyncSessionLocal
from accessmesh.domain.enums import Environment, ResourceType, SubjectType


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(DemoUser.id).limit(1))
        if existing is not None:
            return

        session.add_all(
            [
                DemoUser(
                    external_id="user-requester",
                    username="requester",
                    display_name="演示申请人",
                    role="requester",
                    subject_type=SubjectType.EMPLOYEE,
                    department="支付研发部",
                ),
                DemoUser(
                    external_id="user-approver",
                    username="approver",
                    display_name="演示审批人",
                    role="approver",
                    subject_type=SubjectType.EMPLOYEE,
                    department="平台安全部",
                ),
                DemoUser(
                    external_id="user-auditor",
                    username="auditor",
                    display_name="演示审计员",
                    role="auditor",
                    subject_type=SubjectType.EMPLOYEE,
                    department="内部审计部",
                ),
                DemoUser(
                    external_id="user-contractor",
                    username="contractor",
                    display_name="演示外包人员",
                    role="requester",
                    subject_type=SubjectType.CONTRACTOR,
                    department="外部协作组",
                ),
            ]
        )
        session.add_all(
            [
                Resource(
                    external_id="gitlab:payment-service",
                    name="支付服务代码仓库",
                    resource_type=ResourceType.GITLAB,
                    environment=Environment.TEST,
                    sensitivity="L2",
                    owner_external_id="user-approver",
                    allowed_permissions=["guest", "reporter", "developer", "maintainer"],
                ),
                Resource(
                    external_id="database:payment-test",
                    name="支付测试数据库",
                    resource_type=ResourceType.DATABASE,
                    environment=Environment.TEST,
                    sensitivity="L2",
                    owner_external_id="user-approver",
                    allowed_permissions=["connect", "read_only", "read_write"],
                ),
                Resource(
                    external_id="database:payment-prod",
                    name="支付生产数据库",
                    resource_type=ResourceType.DATABASE,
                    environment=Environment.PRODUCTION,
                    sensitivity="L4",
                    owner_external_id="user-approver",
                    allowed_permissions=["connect", "read_only", "read_write", "ddl_admin"],
                ),
            ]
        )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
