# DigiBook Database: Business Analyst Reference

## Executive Summary
The DigiBook database supports business operations by managing Users, Accounts (clients/companies), and OBM (Order Book Management) records. The schema is modeled after Salesforce, enabling tracking of user roles, account ownership, and order/project details, with clear relationships between users, accounts, and orders.

---

## Table Overview

### 1. User Table
**Purpose:** Stores user identity, role, and organizational details.

**Key Fields:**
- **Id:** Unique user identifier (primary key)
- **Username, Email:** User login and contact
- **Department, Title:** Organizational context
- **UserRoleId:** Role assignment (affects data visibility)
- **EmployeeNumber:** Internal HR code

**Relationships:**
- Referenced by Account and OBM tables for ownership and audit tracking.

**What this means for a Business Analyst:**
- Use this table to identify users, their roles, and organizational placement. Useful for access control, reporting, and understanding who owns or modifies records.

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
**Purpose:** Stores client/company account information, including ownership, industry, and classification.

**Key Fields:**
- **Id, SFDC_Account_Number__c:** Unique account identifiers (composite primary key)
- **Name, Industry, Website:** Client/company details
- **OwnerId, CreatedById, LastModifiedById:** User references for account lifecycle
- **Account_Type__c, Vertical, Sub-Vertical_SF:** Classification and segmentation

**Relationships:**
- OwnerId, CreatedById, LastModifiedById reference User(Id)
- Referenced by OBM for associating orders with accounts

**What this means for a Business Analyst:**
- Analyze client portfolios, segment accounts by industry or type, and track account ownership and changes. Supports client management and reporting.

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
**Purpose:** Stores order book management records (orders, proposals, projects).

**Key Fields:**
- **id, Name:** Unique order identifiers (composite primary key)
- **Proposal_Number__c, Project_Name__c:** Proposal/project linkage
- **Account__c:** Associated client (references Account)
- **PO_Currency__c, PO_Total__c, Total__c:** Financials (original and base currency)
- **CreatedById, LastModifiedById:** User references for record lifecycle
- **Type__c, Opportunity_Type__c, Revenue_Mix__c:** Order classification

**Relationships:**
- Account__c references Account(Id)
- CreatedById, LastModifiedById reference User(Id)

**What this means for a Business Analyst:**
- Track orders and proposals by client, analyze revenue, and monitor project and financial details. Enables reporting on sales, delivery, and client engagement.

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

## Table Relationships (Summary)
- **User** is referenced by **Account** and **OBM** for ownership and audit fields.
- **Account** is referenced by **OBM** for associating orders with clients.

---

## Usage Notes
- Use the data dictionary above for field definitions.
- Use provided Python scripts for data operations.
- Reference relationships for building business queries and reports. 