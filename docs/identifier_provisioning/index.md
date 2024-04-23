# Identifier Provisioning

This gear provisions NACCIDs for data entered with Participant Enrollment and Transfer (PTENRL) forms.

## Processing

The following diagrams describe the processing of the PTRENRL form data.

First, check that the module for the form is the right one, and then determine whether this is a new enrollment or transfer.

```mermaid
graph TB
    start((*)) -->module{module is\nPTENRL} -- no --> moduleerror((error))
    module -- yes --> enrltype{Is new\nenrollment?}
    enrltype -- yes --> newenrollment(New Enrollment)    
    enrltype -- no --> transfer(Transfer)
    newenrollment --> stop((done))
    transfer --> stop
style start fill:#000, stroke:#000
```

### New Enrollment

A new enrollment involves a series of validations that result in errors if the identifying information is inconsistent.
The last step checks the demographics, and if any NACCIDs exists with matching demographics, an error is reported.
In this case, someone will need to manually check the match.
If there are no existing participants that could be matches, then a new NACCID is provisioned.

```mermaid
graph TB
    start((*)) --> naccidforptid{Does NACCID\n exist for\n ADCID,PTID?}
    naccidforptid -- yes --> errorptid((error))
    naccidforptid -- no --> naccidforguid{Does NACCID\n exist for\n GUID?}
    naccidforguid -- yes --> errorguid((error))
    naccidforguid -- no --> checkdemographics{Does NACCID\n exist for\n demographics?}
    checkdemographics -- yes --> errordemo((error))
    checkdemographics -- no --> provision(Provision new NACCID) --> stop((done))
style start fill:#000, stroke:#000
```


```mermaid
sequenceDiagram
    Gear->>Identifiers: get(ADCID,PTID)
    alt has NACCID
        Identifiers->>Gear: identifier record
        break when NACCID exists
            Gear->>File: exists error
        end
    else no match
        Identifiers->>Gear: no match error
        Gear->>Demographics: get(demographics)
        Demographics->>Gear: NACCID list
        alt has matches
          break when list not empty
              Gear->>File: demographic match error
          end
        else no match
            Gear->>Identifiers: add(ADCID,PTID,GUID)
            Identifiers->>Gear: NACCID
            Gear->>Demographics: add(NACCID,demographics)
        end

    end
```

### Transfer

A transfer could either be for the receiving center or the previous center.
The form has a slight ambiguity about whether it is a transfer out of a center or into a center.
This is due to asking both whether the participant was previously enrolled and whether the participant is transferring out.
This is handled by first checking the response for whether they are transferring elsewhere, and, if so, not checking the information about the previous center.

```mermaid
graph TB
    start((*)) --> transferout{Transferring\n elsewhere?}
    transferout -- yes --> transferout(Transfer Out) --> stop((done))
    transferout -- no --> prevenrolled{Was\n previously\n enrolled?}
    prevenrolled -- yes --> transferin(Transfer In)  --> stop((done))
    prevenrolled -- no --> whattransfer((error)) 
style start fill:#000, stroke:#000
```

When a form represents transferring out of a center, the goal is to either

* identify a corresponding incoming transfer, or
* create a record of the pending outgoing transfer

```mermaid
graph TB
    start((*)) --> matchpendingtransfer{Does a pending\n transfer exactly\n match?}
    matchpendingtransfer -- yes --> recordtransfer(Associate NACCID\n and record transfer) --> stop((done))
    matchpendingtransfer -- no --> logtransfer(Record pending\n outgoing transfer\n in enrollment metadata) --> stop((done))
style start fill:#000, stroke:#000
```

When a form represents transferring into a center, the goal is to

* identify the participant by NACCID
* confirm that the participant has transferred
* link new identifiers to the NACCID


```mermaid
graph TB
    start((*)) --> oldptidknown{Is old\n PTID known?}
    oldptidknown -- yes --> naccidforoldptid{Does NACCID\n exist for PTID\n of previous\n enrollment?}
    oldptidknown -- no --> identifytransfer(Record pending\n incoming transfer\n needing identification) --> identifyerror((error))
    naccidforoldptid -- yes --> naccidprovided{Is NACCID\n provided?}
    naccidforoldptid -- no --> nonaccid((error))
    naccidprovided -- yes --> existingnaccid{Does\n provided\n NACCID\n match?}
    naccidprovided -- no --> recordpending1(Record pending\n incoming transfer\n needing confirmation) --> pendingerror2((error))

    existingnaccid -- yes --> matchpendingtransfer{Does a pending\n transfer exactly\n match?}
    existingnaccid -- no --> mismatch((error))
    matchpendingtransfer -- yes --> recordtransfer(Associate NACCID\n and record transfer) --> stop((done))
    matchpendingtransfer -- no --> recordpending(Record pending\n incoming transfer\n waiting for match) --> pendingerror((error))
style start fill:#000, stroke:#000
```

Only the case where 
