# -*- coding: utf-8 -*-
"""
.. module:: pytfa
   :platform: Unix, Windows
   :synopsis: Thermodynamic constraints for Flux-Based Analysis of reactions

.. moduleauthor:: pyTFA team

Constraints declarations

"""

from ..utils.str import camel2underscores

###################################################
###                 CONSTRAINTS                 ###
###################################################


class GenericConstraint:
    """
    Class to represent a generic constraint. The purpose is that the interface
     is instantiated on initialization, to follow the type of interface used
     by the problem, and avoid incompatibilities in optlang

    Attributes:

        :id: Used for DictList comprehension. Usually points back at a
        metabolite or reaction id for ease of linking. Should be unique given
        a constraint type.
        :name: Should be a concatenation of the id and a prefix that is
        specific to the variable type. will be used to address the constraint at
        the solver level, and hence should be unique in the whole model
        :expr: the expression of the constraint (sympy.Expression subtype)
        :model: the model hook.
        :constraint: links directly to the model representation of tbe constraint
    """


    @property
    def __attrname__(self):
        """
        Name the attribute the instances will have
        Example: GenericConstraint -> generic_constraint
        :return:
        """
        return camel2underscores(self.__class__.__name__)

    def __init__(self, id, expr, model, **kwargs):
        """

        :param id: will be used to identify the variable
            (name will be a concat of this and a prefix)
        :param problem: the cobra.Model.problem object
        :param kwargs: stuff you want to pass to the variable constructor
        """
        self._id = id
        self._model = model
        self.kwargs = kwargs
        self._name = self.make_name()
        self.get_interface(expr)

    def get_interface(self, expr):
        """
        Called upon completion of __init__, initializes the value of self.var,
        which is returned upon call, and stores the actual interfaced variable.

        :return: instance of Variable from the problem
        """
        if not self.name in self.model.constraints:
            constraint = self.model.problem.Constraint(expression = expr,
                                                       name = self.name,
                                                       **self.kwargs)
            self.model.add_cons_vars(constraint)
        else:
            self.constraint = self.model.constraints.get(self.name)


    def make_name(self):
        """
        Needs to be overridden by the subclass, concats the id with a
         prefix

        :return: None
        """
        return self.id

    @property
    def expr(self):
        return self.constraint.expression

    @expr.setter
    def expr(self,value):
        self.constraint.expression = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def id(self):
        """
        for cobra.core.DictList compatibility
        :return:
        """
        return self._id

    @property
    def constraint(self):
        return self.model.constraints[self.name]

    @constraint.setter
    def constraint(self, value):
        self.model.constraints[self.name] = value

    @property
    def model(self):
        return self._model

    def __repr__(self):
        return self.name + ': ' + self.constraint.expression.__repr__()


class ReactionConstraint(GenericConstraint):
    """
    Class to represent a variable attached to a reaction
    """

    def __init__(self, reaction, expr, **kwargs):
        self.reaction = reaction
        model = reaction.model

        GenericConstraint.__init__( self,
                                    id=self.id,
                                    expr=expr,
                                    model=model,
                                    **kwargs)


    @property
    def id(self):
        return self.reaction.id

    @property
    def model(self):
        return self.reaction.model

class MetaboliteConstraint(GenericConstraint):
    """
    Class to represent a variable attached to a reaction
    """

    def __init__(self, metabolite, expr, **kwargs):
        self.metabolite = metabolite
        model = metabolite.model

        GenericConstraint.__init__( self,
                                    id=self.id,
                                    expr=expr,
                                    model=model,
                                    **kwargs)

    @property
    def id(self):
        return self.metabolite.id

    @property
    def model(self):
        return self.metabolite.model

class NegativeDeltaG(ReactionConstraint):
    """
    Class to represent thermodynamics constraints.

    G: - DGR_rxn + DGoRerr_Rxn + RT * StoichCoefProd1 * LC_prod1
       + RT * StoichCoefProd2 * LC_prod2
       + RT * StoichCoefSub1 * LC_subs1
       + RT * StoichCoefSub2 * LC_subs2
       - ...
     = 0
    """

    def make_name(self):
        return 'G_' + self.id

class ForwardDeltaGCoupling(ReactionConstraint):
    """
    Class to represent thermodynamics coupling: DeltaG of reactions has to be
    DGR < 0 for the reaction to proceed forwards
    Looks like:
    FU_rxn: 1000 FU_rxn + DGR_rxn < 1000
    BU_rxn: 1000 BU_rxn - DGR_rxn < 1000
    """

    def __init__(self, reaction, expr, **kwargs):
        ReactionConstraint.__init__(self, reaction, expr, **kwargs)

    def make_name(self):
        return 'FU_' + self.id
        
class BackwardDeltaGCoupling(ReactionConstraint):
    """
    Class to represent thermodynamics coupling: DeltaG of reactions has to be
    DGR < 0 for the reaction to proceed forwards
    Looks like:
    BU_rxn: 1000 BU_rxn - DGR_rxn < 1000
    """

    def __init__(self, reaction, expr, **kwargs):
        ReactionConstraint.__init__(self, reaction, expr, **kwargs)

    def make_name(self):
        return 'BU_' + self.id

class ForwardDirectionCoupling(ReactionConstraint):
    """
    Class to represent a directionality coupling with thermodynamics on reaction
    variables
    Looks like :
    UF_rxn: F_rxn - M FU_rxn < 0
    UR_rxn: R_rxn - M RU_rxn < 0
    """

    def __init__(self, reaction, expr, **kwargs):
        ReactionConstraint.__init__(self, reaction, expr, **kwargs)

    def make_name(self):
        return 'UF_' + self.id


class BackwardDirectionCoupling(ReactionConstraint):
    """
    Class to represent a directionality coupling with thermodynamics on reaction
    variables
    Looks like :
    UR_rxn: R_rxn - M RU_rxn < 0
    """

    def __init__(self, reaction, expr, **kwargs):
        ReactionConstraint.__init__(self, reaction, expr, **kwargs)

    def make_name(self):
        return 'UR_' + self.id

class SimultaneousUse(ReactionConstraint):
    """
    Class to represent a simultaneous use constraint on reaction variables
    Looks like:
    SU_rxn: FU_rxn + BU_rxn <= 1
    """

    def make_name(self):
        return 'SU_' + self.id

class DisplacementCoupling(ReactionConstraint):
    """
    Class to represent the coupling to the thermodynamic displacement
    Looks like:
    Ln(Gamma) - (1/RT)*DGR_rxn = 0
    """

    def make_name(self):
        return 'DC_' + self.id

class ForbiddenProfile(GenericConstraint):
    """
    Class to represent a forbidden net flux directionality profile
    Looks like:
    FU_rxn_1 + BU_rxn_2 + ... + FU_rxn_n <= n-1
    """

    def __init__(self, model, expr, id, **kwargs):

        GenericConstraint.__init__( self,
                                    id=id,
                                    expr=expr,
                                    model=model,
                                    **kwargs)

    def make_name(self):
        return 'FP_' + self.id