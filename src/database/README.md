# DigiBook Database Documentation

## Overview

The `digibook.db` SQLite database is designed to support business operations by storing and managing user, account, and order book (OBM) data. The schema is structured to reflect Salesforce-like data models, supporting relationships between users, accounts, and order records.

---

## Table Structure

### 1. User Table
- **Purpose:** Stores information about users in the system, including their identity, role, and organizational details.
- **Primary Key:** `Id`

#### Data Dictionary
| Column           | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| Id               | Unique Salesforce User ID that identifies each user in the system.          |
| Username         | User's login name, typically in the format of an email address.             |
| LastName         | User’s last name or surname.                                                |
| FirstName        | User’s first name or given name.                                            |
| Name             | Full name of the user, usually a concatenation of FirstName and LastName.   |
| Department       | The department or business unit the user belongs to (e.g., Sales, Marketing, Finance). |
| Title            | User's designation (e.g., Associate Manager, Manager, Director)             |
| Email            | Official email address of the user.                                         |
| UserRoleId       | ID of the user’s assigned role in Salesforce, which affects data visibility and hierarchy. |
| EmployeeNumber   | Internal employee ID or code used within the organization for HR or reporting purposes. |

---

### 2. Account Table
- **Purpose:** Stores information about client or company accounts, including ownership, industry, and classification details.
- **Primary Key:** `Id, SFDC_Account_Number__c`
- **Foreign Keys:** `OwnerId`, `CreatedById`, `LastModifiedById` reference `User(Id)`

#### Data Dictionary
| Column                   | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| Id                       | Unique Salesforce ID for the Account record.                                |
| IsDeleted                | Indicates whether the account has been deleted (TRUE/FALSE).                |
| MasterRecordId           | If the account is a duplicate, this field stores the ID of the master record it is merged into. |
| Name                     | Name of the Account (typically the company or client name).                 |
| ParentId                 | References the parent account if this account is a subsidiary or part of a larger organization. |
| Website                  | Company’s official website URL.                                             |
| Industry                 | The industry the account belongs to (e.g., Retail, Pharma, BFSI).           |
| OwnerId                  | Salesforce User ID of the Account Owner (Salesperson/Account Manager).      |
| CreatedDate              | Date and time when the account was created.                                 |
| CreatedById              | Salesforce User ID of the person who created the account.                   |
| LastModifiedDate         | Date and time when the account record was last modified.                    |
| LastModifiedById         | Salesforce User ID of the person who last updated the account.              |
| AccountSource            | Source of account creation (e.g., Web, Partner Referral, Data Upload).      |
| SicDesc                  | Standard Industrial Classification (SIC) description of the business activity. |
| Account_Type__c          | Custom field denoting internal classification (e.g., Client, Partner, Prospect). |
| SFDC_Account_Number__c   | Unique internal account number assigned in Salesforce for tracking purposes. |
| Sub-Vertical_SF          | Sub-industry or niche focus area within the main vertical (e.g., Personal Care within CPG). |
| Vertical                 | Primary industry vertical categorization for strategic segmentation (e.g., Healthcare, BFSI). |

---

### 3. OBM Table
- **Purpose:** Stores order book management (OBM) records, representing order entries, proposals, and project details.
- **Primary Key:** `id, Name`
- **Foreign Keys:** `Account__c` references `Account(Id)`, `CreatedById` and `LastModifiedById` reference `User(Id)`

#### Data Dictionary
| Column                                         | Description                                                                 |
|------------------------------------------------|-----------------------------------------------------------------------------|
| id                                             | Unique Salesforce record identifier for the order entry.                    |
| IsDeleted                                      | Indicates whether the record is deleted (TRUE or FALSE).                   |
| Name                                           | System-generated Easy Unique ID of the order book record.                   |
| Proposal_Number__c                             | Unique identifier of the proposal associated with this order.              |
| Project_Name__c                                | Name or title of the project linked to the proposal. One Proposal number may have multiple records with diff project names |
| Account__c                                     | Salesforce account (client) associated with the order.                     |
| PO_Currency__c                                 | Currency code of the Purchase Order (e.g., USD, INR).                      |
| PO_Total__c                                    | Total amount in the original PO currency.                                  |
| Month__c                                       | Month in which the order is booked                                         |
| Year__c                                        | Fiscal year corresponding to the PO or order.                              |
| CurrencyIsoCode                                | Standard currency code used for multi-currency organizations.              |
| Total__c                                       | Total amount of the order in the organization’s base currency (USD). This is the amount accrued for particular record/line item |
| CreatedDate                                    | Date the record was created in Salesforce.                                 |
| CreatedById                                    | Salesforce User ID of the person who created the record.                   |
| LastModifiedDate                               | Date when the record was last modified.                                    |
| LastModifiedById                               | Salesforce User ID of the person who last modified the record.             |
| Country_Bill_to_Budget_owning_geo__c           | Geographic region responsible for the billing and budget.                  |
| Country_Ship_to_The_End_Client_Geo__c          | End-client's delivery geography or region.                                 |
| Course5_Location__c                            | Course5’s internal delivery location for the project.                      |
| End_Client_Name_POC__c                         | Name of the end client's point of contact (POC).                           |
| FTE_Name__c                                    | Full-Time Equivalent (FTE) employee(s) associated with the project.        |
| Finance_Check__c                               | Status or notes from the finance team's validation process.                |
| If_US_State_Name__c                            | U.S. state name, if the client location is within the United States.       |
| Type__c                                        | Type of order (e.g., New, Renewal, Amendment).                             |
| Offshore_Location__c                           | Offshore delivery location (typically Course5 office in India).            |
| Onshore_Location__c                            | Onshore delivery location (typically at or near client site).              |
| Opportunity_Closed__c                          | This is used to link it with Opportunity Closure Form Table                |
| Opportunity_Type__c                            | Type of opportunity (e.g., RAI, MMM, etc.).                                |
| Client_Geography_Tagging__c                    | Geographical tagging of the client based on internal mapping.              |
| PO_Date__c                                     | Date on which the Purchase Order was issued.                               |
| PO_Number__c                                   | Unique number of the client’s Purchase Order.                              |
| Primary_Flag__c                                | Services/Products                                                          |
| SOW_Number__c                                  | Statement of Work (SOW) number linked to this order.                       |
| Secondary_Flag_2__c                            | Onsite/Offshore                                                            |
| Secondary_Flag__c                              | Offshore/ Data Processing/ Survey Programming, etc.                        |
| UDS_Value_Of_PO_Total__c                       | Value of the PO converted to USD, used for unified reporting.              |
| Vendor_Cost_Currency__c                        | Currency in which vendor costs are tracked.                                |
| Vendor_Cost_USD__c                             | Vendor cost converted to USD.                                              |
| Vendor_Costs__c                                | Total cost associated with third-party vendors for this project.           |
| Sales_lead__c                                  | Name of the sales lead responsible for this opportunity.                   |
| Delivery_Team_Name__c                          | Internal Course5 delivery team managing the execution.                     |
| Employee_name_in_Course5_to_confirm_bill__c    | Employee accountable for confirming billing with the client.               |
| Child_company_name__c                          | If the order is for a subsidiary or sub-brand of the main client.          |
| Delivery_Capability__c                         | Specific delivery capability (e.g., AI, Insights, Data Engineering).       |
| Owner__c                                       | Salesforce User ID of the record owner (typically Sales owner).            |
| Pricing_Model__c                               | Commercial pricing model (e.g., T&M, Fixed Bid, Retainer).                 |
| Revenue_Mix__c                                 | Revenue classification (e.g., Services, License, Pass-through).            |
| Primary_Practice__c                            | The Primary practice group (e.g., Pharma CI, UI/UX, Data Engg, etc.) involved. |
| Type_of_Contracts__c                           | Type of contract signed (e.g., T&M-FTE, Output Based, etc.)                |
| Secondary_Practice__c                          | Additional practice contributing to the engagement.                        |
| Primary_Functionality__c                       | The domain of problem being solved for the client like HR/Marketing/supplu Chain, etc. |
| Primary_Capability__c                          | Key internal capability aligned with the delivery (e.g., Advanced Analytics). |
| Engagement_Model__c                            | Type of client engagement (e.g., FTE-based, project-based).                |
| Platforms_c__c                                 | Platforms/tools used in the project (multi-select lookup).                 |
| Platforms__c                                   | Platforms/tools used in the project (multi-select lookup).                 |

---

## Relationships
- **User** is referenced by both **Account** and **OBM** tables for ownership and audit fields.
- **Account** is referenced by **OBM** for associating orders with clients.

---

## Usage
- Use the provided Python scripts to insert, update, or query data.
- The data dictionary above should be referenced for understanding the meaning and purpose of each field. 